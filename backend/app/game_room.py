"""Game Room Manager for Six Second Scribbles.

Architecture: Server-side scoring with client-side card assignment.
- Server accumulates guesses and scores rounds using rapidfuzz
- Host client handles card assignment and round timing
- Server broadcasts round_complete and game_complete
"""
# spell-checker: ignore reconnections

import asyncio
import contextlib
import json
import logging
import random
import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

from app.config import settings
from app.scoring import guess_matcher

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)


def _create_logged_task(coro, name: str) -> asyncio.Task:
    """Create a fire-and-forget task that logs any unhandled exception."""
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(
        lambda t: logger.error("[Task %s] unhandled exception: %s", name, t.exception())
        if not t.cancelled() and t.exception()
        else None,
    )
    return task


@dataclass
class PlayerInfo:
    """Information about a player in a game room."""

    id: str
    name: str
    websocket: "WebSocket"
    categories: list[str] = field(default_factory=list)
    last_activity: float = field(default_factory=time.time)


@dataclass
class KickVote:
    """Tracks votes to kick a player."""

    target_player_id: str
    target_player_name: str
    initiated_by: str
    voters: set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 60)  # 1 minute


@dataclass
class RoomMetadata:
    """Metadata and state information for a game room."""

    categories: list[str] = field(default_factory=list)
    game_phase: str = "lobby"
    round_start_time: int | None = None
    round_length: int | None = None
    difficulty: str = "medium"
    max_rounds: int = 5
    current_round: int = 0
    pad_visibility: bool = True
    ready_players: set[str] = field(default_factory=set)
    is_private: bool = False  # Private rooms don't appear in random join
    language: str = "en"  # Language code (ISO 639-1): en, es, fr, etc.
    # Server-side scoring state
    player_cards: dict[str, dict[str, Any]] = field(default_factory=dict)  # playerId -> {category, items, ...}
    guess_submissions: list[dict[str, Any]] = field(default_factory=list)  # [{playerId, targetPlayerId, guesses}]
    submitted_players: set[str] = field(default_factory=set)  # playerIds that have submitted at least once
    player_count_for_scoring: int = 0  # expected number of submitters (snapshot at start_guessing)
    player_scores: dict[str, int] = field(default_factory=dict)  # playerId -> cumulative score


class GameRoom:
    """Manages a single game room with multiple players."""

    # Kick vote timeout (1 minute) — not yet configurable via settings
    KICK_VOTE_TIMEOUT_SECONDS = 60

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: dict[str, PlayerInfo] = {}
        self.host_id: str | None = None
        self.metadata = RoomMetadata()
        self._idle_check_task: asyncio.Task | None = None
        self._pending_host_transfer: asyncio.Task | None = None
        self._round_scoring_task: asyncio.Task | None = None
        self._scoring_lock = asyncio.Lock()
        self._last_host_id: str | None = None  # Track last host for reconnection
        self._created_at = time.time()
        self._last_activity = time.time()
        self._emptied_at: float | None = None  # When room became empty
        self.is_hibernated = False
        self.active_kick_votes: dict[str, KickVote] = {}  # target_player_id -> KickVote

    async def score_and_broadcast_round(self):
        """Score submitted guesses with fuzzy matching and broadcast round_complete."""
        async with self._scoring_lock:
            await self._score_and_broadcast_round_locked()

    async def _score_and_broadcast_round_locked(self):
        """Inner scoring logic, must be called under self._scoring_lock."""
        if self._round_scoring_task:
            self._round_scoring_task.cancel()
            self._round_scoring_task = None

        results = []
        round_points: dict[str, int] = dict.fromkeys(self.players, 0)

        for submission in self.metadata.guess_submissions:
            player_id = submission["playerId"]
            target_player_id = submission["targetPlayerId"]
            guesses = submission["guesses"]

            target_card = self.metadata.player_cards.get(target_player_id)
            if not target_card:
                logger.warning("[GameRoom %s] No card found for player %s, skipping", self.room_id, target_player_id)
                continue

            correct_items = target_card.get("items", [])
            scoring_result = guess_matcher.score_guesses(guesses, correct_items)
            correct_count = scoring_result["score"]
            points_earned = correct_count * 10

            if player_id in round_points:
                round_points[player_id] += points_earned
            if target_player_id in round_points:
                round_points[target_player_id] += points_earned

            results.append(
                {
                    "playerId": player_id,
                    "targetPlayerId": target_player_id,
                    "correctGuesses": correct_count,
                    "totalItems": len(correct_items),
                    "pointsEarned": points_earned,
                },
            )

        # Update cumulative scores
        for pid, points in round_points.items():
            self.metadata.player_scores[pid] = self.metadata.player_scores.get(pid, 0) + points

        self.metadata.game_phase = "scoring"
        await self.broadcast(
            {
                "type": "round_complete",
                "results": results,
                "scores": dict(self.metadata.player_scores),
            },
        )

        logger.info(
            "[GameRoom %s] Round %s/%s scored. Scores: %s",
            self.room_id,
            self.metadata.current_round,
            self.metadata.max_rounds,
            self.metadata.player_scores,
        )

        await self.persist()

        # On the final round, broadcast game_complete after countdown
        if self.metadata.current_round >= self.metadata.max_rounds:
            _create_logged_task(
                self._broadcast_game_complete_after_delay(),
                name=f"game_complete_{self.room_id}",
            )

    async def _broadcast_game_complete_after_delay(self):
        """Wait for the round-results countdown, then broadcast game_complete."""
        await asyncio.sleep(5)
        winner_id = (
            max(self.metadata.player_scores, key=lambda pid: self.metadata.player_scores[pid])
            if self.metadata.player_scores
            else ""
        )
        self.metadata.game_phase = "complete"
        await self.broadcast(
            {
                "type": "game_complete",
                "finalScores": dict(self.metadata.player_scores),
                "winner": winner_id,
            },
        )
        logger.info("[GameRoom %s] Game complete. Winner: %s", self.room_id, winner_id)
        await self.persist()

    def start_scoring_timeout(self, timeout_seconds: int):
        """Start a fallback scoring task in case not all players submit in time."""
        if self._round_scoring_task:
            self._round_scoring_task.cancel()
        self._round_scoring_task = _create_logged_task(
            self._scoring_timeout(timeout_seconds),
            name=f"scoring_timeout_{self.room_id}",
        )

    async def _scoring_timeout(self, timeout_seconds: int):
        try:
            await asyncio.sleep(timeout_seconds + 3)  # small buffer after guessing phase ends
            submitted = len(self.metadata.submitted_players)
            expected = self.metadata.player_count_for_scoring
            logger.info(
                "[GameRoom %s] Scoring timeout: %s/%s players submitted. Scoring now.",
                self.room_id,
                submitted,
                expected,
            )
            await self.score_and_broadcast_round()
        except asyncio.CancelledError:
            pass

    async def start_idle_check(self):
        """Start periodic idle player check"""
        self._idle_check_task = _create_logged_task(
            self._idle_check_loop(),
            name=f"idle_check_{self.room_id}",
        )

    async def stop_idle_check(self):
        """Stop idle player check and any pending scoring tasks."""
        if self._idle_check_task:
            self._idle_check_task.cancel()
            try:
                await self._idle_check_task
            except asyncio.CancelledError:
                pass
        if self._round_scoring_task:
            self._round_scoring_task.cancel()
            self._round_scoring_task = None

    async def _idle_check_loop(self):
        """Periodically check for idle players and cleanup expired votes"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                await self._check_idle_players()
                self.cleanup_expired_votes()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[GameRoom %s] Error in idle check", self.room_id)

    async def _check_idle_players(self):
        """Check for and disconnect idle players during active game phases"""
        if self.metadata.game_phase not in ["lobby", "complete"]:
            now = time.time()
            idle_players = []

            for player_id, player in self.players.items():
                idle_time = now - player.last_activity
                if idle_time > settings.idle_timeout_seconds:
                    logger.info(
                        "[GameRoom %s] Player %s (%s) is idle for %ss",
                        self.room_id,
                        player.name,
                        player_id,
                        idle_time,
                    )
                    idle_players.append(player_id)

            # Disconnect idle players
            for player_id in idle_players:
                player = self.players.get(player_id)
                if player:
                    logger.info("[GameRoom %s] Disconnecting idle player: %s", self.room_id, player.name)
                    with contextlib.suppress(Exception):
                        await player.websocket.close(code=1000, reason="Disconnected due to inactivity")

    async def add_player(self, player_id: str, name: str, websocket: "WebSocket"):
        """Add a player to the room

        Returns tuple: (player, is_reconnecting_host)
        Raises ValueError if room is full
        """
        # Check if room is at capacity (but allow existing player to reconnect)
        if player_id not in self.players and len(self.players) >= settings.max_players:
            raise ValueError(f"Room is full (maximum {settings.max_players} players)")

        # Room is no longer empty - wake from hibernation if needed
        if self.is_hibernated:
            logger.info("[GameRoom %s] Waking from hibernation", self.room_id)
            self.is_hibernated = False

        self._last_activity = time.time()
        self._emptied_at = None

        # Check if this is the previous host reconnecting
        is_reconnecting_host = player_id == self._last_host_id and player_id not in self.players

        player = PlayerInfo(
            id=player_id,
            name=name,
            websocket=websocket,
            last_activity=time.time(),
        )
        self.players[player_id] = player

        # Cancel pending host transfer if the host reconnected
        if is_reconnecting_host and self._pending_host_transfer:
            self._pending_host_transfer.cancel()
            self._pending_host_transfer = None
            self.host_id = player_id
            logger.info(
                "[GameRoom %s] Host %s (%s) reconnected, host transfer cancelled",
                self.room_id,
                name,
                player_id,
            )

        # If this is the first player, make them host
        elif len(self.players) == 1:
            self.host_id = player_id
            self._last_host_id = player_id

        return player, is_reconnecting_host

    async def remove_player(self, player_id: str):
        """Remove a player from the room"""
        if player_id in self.players:
            del self.players[player_id]

        # Mark when room becomes empty
        if len(self.players) == 0:
            self._emptied_at = time.time()
            logger.info("[GameRoom %s] Room is now empty, marked for hibernation/cleanup", self.room_id)

        # Handle host transfer if the host left
        if player_id == self.host_id:
            if len(self.players) > 0:
                # Schedule delayed host transfer to allow for reconnection
                logger.info(
                    "[GameRoom %s] Host disconnected, scheduling transfer in %sms...",
                    self.room_id,
                    settings.host_transfer_delay_ms,
                )

                # Cancel any existing pending transfer
                if self._pending_host_transfer:
                    self._pending_host_transfer.cancel()

                # Schedule new transfer
                self._pending_host_transfer = _create_logged_task(
                    self._delayed_host_transfer(player_id),
                    name=f"host_transfer_{self.room_id}",
                )
            else:
                # No players left, room is effectively closed
                self.host_id = None
                self._last_host_id = None

    async def _delayed_host_transfer(self, old_host_id: str):
        """Transfer host after a delay, allowing for reconnection"""
        try:
            # Wait for the delay
            await asyncio.sleep(settings.host_transfer_delay_ms / 1000)

            # Check if host reconnected during the delay
            if old_host_id in self.players:
                logger.info("[GameRoom %s] Host reconnected, cancelling transfer", self.room_id)
                self.host_id = old_host_id
                return

            # Transfer host if there are still players
            if len(self.players) > 0:
                new_host = next(iter(self.players.values()))
                self.host_id = new_host.id
                self._last_host_id = new_host.id

                # Notify all remaining players of the new host
                await self.broadcast({"type": "host_changed", "newHostId": new_host.id})

                logger.info("[GameRoom %s] Host transferred to %s (%s)", self.room_id, new_host.name, new_host.id)
            else:
                self.host_id = None
                self._last_host_id = None

        except asyncio.CancelledError:
            logger.info("[GameRoom %s] Host transfer cancelled (host reconnected)", self.room_id)
        finally:
            self._pending_host_transfer = None

    def update_player_activity(self, player_id: str):
        """Update the last activity timestamp for a player"""
        if player_id in self.players:
            self.players[player_id].last_activity = time.time()

    async def broadcast(self, message: dict, exclude: str | None = None):
        """Broadcast a message to all players in the room."""
        message_str = json.dumps(message)
        disconnected_players = []

        for player_id, player in self.players.items():
            if exclude and player_id == exclude:
                continue
            try:
                await player.websocket.send_text(message_str)
            except Exception:
                logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
                disconnected_players.append(player_id)

        # Clean up disconnected players after the loop (safe: we snapshotted the list)
        for player_id in disconnected_players:
            await self.remove_player(player_id)
            await self.broadcast({"type": "player_left", "playerId": player_id})

    async def send_to_player(self, player_id: str, message: dict):
        """Send a message to a specific player"""
        if player_id in self.players:
            player = self.players[player_id]
            try:
                await player.websocket.send_text(json.dumps(message))
            except Exception:
                logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
                await self.remove_player(player_id)

    def get_player_list(self) -> list[dict[str, str]]:
        """Get the list of all players in the room"""
        return [{"id": p.id, "name": p.name} for p in self.players.values()]

    async def initiate_kick_vote(self, initiator_id: str, target_player_id: str) -> dict:
        """Initiate a vote to kick a player

        Returns dict with status and info about the vote
        """
        # Validate players exist
        if initiator_id not in self.players:
            return {"success": False, "error": "Initiator not in room"}

        if target_player_id not in self.players:
            return {"success": False, "error": "Target player not in room"}

        # Can't kick yourself
        if initiator_id == target_player_id:
            return {"success": False, "error": "Cannot kick yourself"}

        # Check if vote already exists
        if target_player_id in self.active_kick_votes:
            vote = self.active_kick_votes[target_player_id]
            if time.time() < vote.expires_at:
                return {"success": False, "error": "Vote already in progress"}
            # Clean up expired vote
            del self.active_kick_votes[target_player_id]

        # Host can kick directly
        is_host_kicking = initiator_id == self.host_id
        target_is_host = target_player_id == self.host_id

        if is_host_kicking and not target_is_host:
            # Host kicks non-host player directly
            await self.kick_player(target_player_id, "Kicked by host")
            return {"success": True, "immediate": True, "reason": "Host kicked player"}

        # Create vote
        target_player = self.players[target_player_id]
        vote = KickVote(
            target_player_id=target_player_id,
            target_player_name=target_player.name,
            initiated_by=initiator_id,
            voters={initiator_id},  # Initiator automatically votes yes
        )
        self.active_kick_votes[target_player_id] = vote

        # Broadcast vote started
        await self.broadcast(
            {
                "type": "kick_vote_started",
                "targetPlayerId": target_player_id,
                "targetPlayerName": target_player.name,
                "initiatedBy": initiator_id,
                "requiredVotes": self._get_required_votes(target_is_host),
                "currentVotes": 1,
                "expiresAt": vote.expires_at * 1000,  # Convert to ms for frontend
            },
        )

        logger.info(
            "[GameRoom %s] Kick vote started for %s by %s",
            self.room_id,
            target_player.name,
            self.players[initiator_id].name,
        )

        return {"success": True, "immediate": False, "vote_id": target_player_id}

    async def cast_kick_vote(self, voter_id: str, target_player_id: str) -> dict:
        """Cast a vote to kick a player"""
        # Validate voter exists
        if voter_id not in self.players:
            return {"success": False, "error": "Voter not in room"}

        # Check if vote exists
        if target_player_id not in self.active_kick_votes:
            return {"success": False, "error": "No active vote for this player"}

        vote = self.active_kick_votes[target_player_id]

        # Check if vote expired
        if time.time() > vote.expires_at:
            del self.active_kick_votes[target_player_id]
            await self.broadcast({"type": "kick_vote_expired", "targetPlayerId": target_player_id})
            return {"success": False, "error": "Vote has expired"}

        # Can't vote to kick yourself
        if voter_id == target_player_id:
            return {"success": False, "error": "Cannot vote to kick yourself"}

        # Add vote
        vote.voters.add(voter_id)

        target_is_host = target_player_id == self.host_id
        required_votes = self._get_required_votes(target_is_host)
        current_votes = len(vote.voters)

        # Broadcast vote update
        await self.broadcast(
            {
                "type": "kick_vote_updated",
                "targetPlayerId": target_player_id,
                "currentVotes": current_votes,
                "requiredVotes": required_votes,
            },
        )

        logger.info(
            "[GameRoom %s] Kick vote: %s/%s for %s",
            self.room_id,
            current_votes,
            required_votes,
            vote.target_player_name,
        )

        # Check if vote passes
        if current_votes >= required_votes:
            await self.kick_player(target_player_id, "Kicked by vote")
            del self.active_kick_votes[target_player_id]
            return {"success": True, "vote_passed": True}

        return {"success": True, "vote_passed": False, "current_votes": current_votes, "required_votes": required_votes}

    def _get_required_votes(self, target_is_host: bool) -> int:
        """Calculate required votes to kick a player"""
        total_players = len(self.players)

        if target_is_host:
            # Need all other players to vote (unanimous)
            return total_players - 1
        # Need 2/3 majority (excluding target)
        eligible_voters = total_players - 1
        return max(2, int((eligible_voters * 2) / 3) + 1)

    async def kick_player(self, player_id: str, reason: str = "Kicked"):
        """Kick a player from the room"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        logger.info("[GameRoom %s] Kicking player %s (%s): %s", self.room_id, player.name, player_id, reason)

        # Close their websocket connection
        try:
            await player.websocket.close(code=1008, reason=reason)
        except Exception:
            logger.exception("[GameRoom %s] Error closing websocket for kicked player", self.room_id)

        # Remove from room
        await self.remove_player(player_id)

        # Broadcast kick event
        await self.broadcast(
            {"type": "player_kicked", "playerId": player_id, "playerName": player.name, "reason": reason},
        )

        # Clean up any vote for this player
        if player_id in self.active_kick_votes:
            del self.active_kick_votes[player_id]

    def cleanup_expired_votes(self):
        """Remove expired kick votes"""
        now = time.time()
        expired = [target_id for target_id, vote in self.active_kick_votes.items() if now > vote.expires_at]

        for target_id in expired:
            del self.active_kick_votes[target_id]
            logger.info("[GameRoom %s] Kick vote expired for player %s", self.room_id, target_id)

        return len(expired)

    # ------------------------------------------------------------------ #
    # Redis persistence                                                    #
    # ------------------------------------------------------------------ #

    def to_redis_dict(self) -> dict:
        """Serialize room state to a JSON-safe dict for Redis storage."""
        meta = asdict(self.metadata)
        # sets are not JSON-serializable — convert to lists
        meta["ready_players"] = list(self.metadata.ready_players)
        meta["submitted_players"] = list(self.metadata.submitted_players)
        return {
            "room_id": self.room_id,
            "host_id": self.host_id,
            "_last_host_id": self._last_host_id,
            "_created_at": self._created_at,
            "_emptied_at": self._emptied_at,
            "is_hibernated": self.is_hibernated,
            "metadata": meta,
        }

    @classmethod
    def from_redis_dict(cls, data: dict) -> "GameRoom":
        """Restore a room from a Redis-persisted dict (no players — they reconnect)."""
        room = cls(data["room_id"])
        room.host_id = data.get("host_id")
        room._last_host_id = data.get("_last_host_id")
        room._created_at = data.get("_created_at", time.time())
        room._emptied_at = data.get("_emptied_at")
        room.is_hibernated = data.get("is_hibernated", False)

        meta = data.get("metadata", {})
        # Restore sets from the serialized lists
        meta["ready_players"] = set(meta.get("ready_players", []))
        meta["submitted_players"] = set(meta.get("submitted_players", []))
        room.metadata = RoomMetadata(**meta)

        return room

    async def persist(self) -> None:
        """Write current room state to Redis."""
        from app.redis_store import save_room_state

        await save_room_state(self.room_id, self.to_redis_dict())

    # ------------------------------------------------------------------ #

    def is_empty(self) -> bool:
        """Check if the room is empty"""
        return len(self.players) == 0

    def should_hibernate(self) -> bool:
        """Check if room should be hibernated (empty for < hibernation timeout)"""
        if not self.is_empty() or self.is_hibernated:
            return False

        if self._emptied_at is None:
            return False

        # Room has been empty for some time but not long enough to be removed
        empty_duration = time.time() - self._emptied_at
        return empty_duration >= 60  # Hibernate after 1 minute of being empty

    def should_be_removed(self) -> bool:
        """Check if room should be permanently removed"""
        if not self.is_empty():
            return False

        if self._emptied_at is None:
            return False

        # Remove room if empty for longer than hibernation timeout
        empty_duration = time.time() - self._emptied_at
        return empty_duration >= settings.room_ttl_seconds

    def get_age_seconds(self) -> float:
        """Get room age in seconds"""
        return time.time() - self._created_at

    def get_empty_duration_seconds(self) -> float | None:
        """Get how long room has been empty, or None if not empty"""
        if self._emptied_at is None:
            return None
        return time.time() - self._emptied_at

    async def hibernate(self):
        """Put room into hibernation mode"""
        if self.is_hibernated or not self.is_empty():
            return

        logger.info("[GameRoom %s] Entering hibernation mode (age: %.0fs)", self.room_id, self.get_age_seconds())
        self.is_hibernated = True

    async def cleanup_custom_categories(self):
        """Delete all custom categories created for this room"""
        try:
            from sqlalchemy import delete

            from app.database import get_session_maker
            from app.db_models import Category

            async with get_session_maker()() as session:
                # Delete all categories with this room_id
                stmt = delete(Category).where(Category.room_id == self.room_id)
                result = await session.execute(stmt)
                await session.commit()

                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.info("[GameRoom %s] Cleaned up %s custom categories", self.room_id, deleted_count)
        except Exception:
            logger.exception("[GameRoom %s] Error cleaning up custom categories", self.room_id)


class RoomManager:
    """Manages all game rooms with PartyKit-like lifecycle

    Features:
    - Automatic hibernation of empty rooms after 1 minute
    - Garbage collection of hibernated rooms after 5 minutes
    - Periodic cleanup every 60 seconds
    """

    # Cleanup interval (1 minute)
    CLEANUP_INTERVAL_SECONDS = 60

    def __init__(self):
        self.rooms: dict[str, GameRoom] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self):
        """Start the room manager and periodic cleanup"""
        if self._is_running:
            return

        self._is_running = True
        await self._restore_from_redis()
        self._cleanup_task = _create_logged_task(
            self._periodic_cleanup_loop(),
            name="room_manager_cleanup",
        )
        logger.info("[RoomManager] Started with cleanup interval of %ss", self.CLEANUP_INTERVAL_SECONDS)

    async def _restore_from_redis(self):
        """Load persisted room states from Redis on startup."""
        from app.redis_store import load_all_room_states

        states = await load_all_room_states()
        for state in states:
            room_id = state.get("room_id")
            if not room_id:
                continue
            room = GameRoom.from_redis_dict(state)
            self.rooms[room_id] = room
            await room.start_idle_check()
        if states:
            logger.info("[RoomManager] Restored %s room(s) from Redis", len(states))

    async def stop(self):
        """Stop the room manager and cleanup tasks"""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clean up all rooms
        for room_id in list(self.rooms.keys()):
            await self.remove_room(room_id)

        logger.info("[RoomManager] Stopped and cleaned up all rooms")

    async def _periodic_cleanup_loop(self):
        """Periodically clean up and hibernate rooms"""
        while self._is_running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                await self._run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[RoomManager] Error in cleanup loop")

    async def _run_cleanup(self):
        """Run cleanup and hibernation checks on all rooms"""
        total_rooms = len(self.rooms)
        hibernated_count = 0
        removed_count = 0

        rooms_to_remove = []
        rooms_to_hibernate = []

        # Check each room
        for room_id, room in list(self.rooms.items()):
            if room.should_be_removed():
                rooms_to_remove.append(room_id)
            elif room.should_hibernate():
                rooms_to_hibernate.append((room_id, room))

        # Hibernate rooms
        for room_id, room in rooms_to_hibernate:
            await room.hibernate()
            hibernated_count += 1

        # Remove old rooms
        for room_id in rooms_to_remove:
            await self.remove_room(room_id)
            removed_count += 1

        if hibernated_count > 0 or removed_count > 0:
            logger.info(
                "[RoomManager] Cleanup: %s total, %s hibernated, %s removed",
                total_rooms,
                hibernated_count,
                removed_count,
            )

    def get_or_create_room(self, room_id: str) -> GameRoom:
        """Get an existing room or create a new one"""
        if room_id not in self.rooms:
            room = GameRoom(room_id)
            self.rooms[room_id] = room
            _create_logged_task(room.start_idle_check(), name=f"idle_check_start_{room_id}")
            logger.info("[RoomManager] Created new room: %s (total rooms: %s)", room_id, len(self.rooms))
        return self.rooms[room_id]

    def get_room(self, room_id: str) -> GameRoom | None:
        """Get an existing room"""
        return self.rooms.get(room_id)

    async def remove_room(self, room_id: str):
        """Remove a room and clean up custom categories"""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            await room.stop_idle_check()
            await room.cleanup_custom_categories()  # Clean up custom categories
            del self.rooms[room_id]
            from app.redis_store import delete_room_state

            await delete_room_state(room_id)
            logger.info("[RoomManager] Removed room %s (total rooms: %s)", room_id, len(self.rooms))

    async def cleanup_empty_rooms(self):
        """Remove all currently empty rooms."""
        empty_rooms = [room_id for room_id, room in self.rooms.items() if room.is_empty()]
        for room_id in empty_rooms:
            await self.remove_room(room_id)

    def get_stats(self) -> dict[str, Any]:
        """Get room manager statistics"""
        total_rooms = len(self.rooms)
        active_rooms = sum(1 for room in self.rooms.values() if not room.is_empty())
        hibernated_rooms = sum(1 for room in self.rooms.values() if room.is_hibernated)
        total_players = sum(len(room.players) for room in self.rooms.values())

        return {
            "total_rooms": total_rooms,
            "active_rooms": active_rooms,
            "hibernated_rooms": hibernated_rooms,
            "empty_rooms": total_rooms - active_rooms - hibernated_rooms,
            "total_players": total_players,
        }

    def find_random_public_room(self, max_players: int = 10) -> str | None:
        """Find a random public room that's available to join

        Criteria:
        - Not private (is_private = False)
        - Not full (< max_players)
        - In lobby phase (not mid-game)
        - Has at least 1 player (not empty)

        Returns room_id if found, None otherwise
        """
        available_rooms = [
            room_id
            for room_id, room in self.rooms.items()
            if not room.metadata.is_private
            and 0 < len(room.players) < max_players
            and room.metadata.game_phase == "lobby"
        ]

        return random.choice(available_rooms) if available_rooms else None


# Global room manager instance
room_manager = RoomManager()
