"""Game Room Manager for Six Second Scribbles.

Architecture: server-driven room and game orchestration.
- Server owns room state, card assignment, phase transitions, scoring, and completion
- Clients render server state and send user actions
- Server broadcasts room, round, and scoring state to all clients
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import delete

from app.categories import service as category_service
from app.categories.models import Category
from app.core.config import settings
from app.core.database import get_session_maker
from app.core.redis import delete_room_state
from app.core.types import (
    COMPLETE_PHASE,
    GUESSING_PHASE,
    LOBBY_PHASE,
    Difficulty,
    GamePhase,
    LanguageCode,
)
from app.rooms import kick_vote, player_lifecycle, rounds
from app.rooms import lifecycle as room_lifecycle
from app.rooms.protocol import (
    PlayerLeftEvent,
    PlayerCardPayload,
    PlayerSnapshot,
    ReadyStatusEvent,
    RoomStateEvent,
    StartRoundBroadcastEvent,
    WebSocketMessage,
    send_ws_message,
)
from app.rooms.state import (  # noqa: TC001 - used in RoomMetadata dataclass field types at runtime
    GuessSubmissionState,
    PlayerCardState,
)

# spell-checker: ignore reconnections

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from fastapi import WebSocket

    from app.rooms.kick_vote import KickVote
    from app.rooms.results import KickVoteResult
    from app.rooms.state import RoomState

logger = logging.getLogger(__name__)


def _create_logged_task(coroutine: Coroutine[object, object, object], name: str) -> asyncio.Task[object]:
    """Create a fire-and-forget task that logs any unhandled exception."""
    task = asyncio.create_task(coroutine, name=name)
    task.add_done_callback(
        lambda t: (
            logger.error("[Task %s] unhandled exception", name, exc_info=t.exception())
            if not t.cancelled() and t.exception()
            else None
        ),
    )
    return task


async def _cancel_task(task: asyncio.Task[object] | None) -> None:
    """Cancel a task and wait for it to finish when needed."""
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


@dataclass
class PlayerInfo:
    """Information about a player in a game room."""

    id: str
    name: str
    websocket: WebSocket
    last_activity: float = field(default_factory=time.time)


@dataclass
class RoomMetadata:
    """Metadata and state information for a game room."""

    categories: list[str] = field(default_factory=list)
    game_phase: GamePhase = "lobby"
    round_start_time: int | None = None
    round_length: int | None = None
    difficulty: Difficulty = "medium"
    max_rounds: int = 5
    current_round: int = 0
    pad_visibility: bool = True
    ready_players: set[str] = field(default_factory=set)
    is_private: bool = False  # Private rooms don't appear in random join
    language: LanguageCode = "en"  # Language code (ISO 639-1): en, es, fr, etc.
    # Server-side scoring state
    player_cards: dict[str, PlayerCardState] = field(default_factory=dict)
    guess_submissions: list[GuessSubmissionState] = field(default_factory=list)
    submitted_players: set[str] = field(default_factory=set)  # playerIds that have submitted at least once
    player_count_for_scoring: int = 0  # expected number of submitters (snapshot at start_guessing)
    player_scores: dict[str, int] = field(default_factory=dict)  # playerId -> cumulative score


class RoomStats(TypedDict):
    """Aggregate room manager statistics."""

    total_rooms: int
    active_rooms: int
    hibernated_rooms: int
    empty_rooms: int
    total_players: int


class GameRoom:
    """Manages a single game room with multiple players."""

    # Kick vote timeout (1 minute) — not yet configurable via settings
    KICK_VOTE_TIMEOUT_SECONDS = 60

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: dict[str, PlayerInfo] = {}
        self.host_id: str | None = None
        self.metadata = RoomMetadata()
        self._idle_check_task: asyncio.Task[object] | None = None
        self._pending_host_transfer: asyncio.Task[object] | None = None
        self._guessing_start_task: asyncio.Task[object] | None = None
        self._next_round_start_task: asyncio.Task[object] | None = None
        self._round_scoring_task: asyncio.Task[object] | None = None
        self._game_complete_task: asyncio.Task[object] | None = None
        self._scoring_lock = asyncio.Lock()
        self._last_host_id: str | None = None  # Track last host for reconnection
        self._created_at = time.time()
        self._last_activity = time.time()
        self._emptied_at: float | None = None  # When room became empty
        self.is_hibernated = False
        self.active_kick_votes: dict[str, KickVote] = {}  # target_player_id -> KickVote

    async def score_and_broadcast_round(self) -> None:
        """Score submitted guesses with fuzzy matching and broadcast round_complete."""
        async with self._scoring_lock:
            await self._score_and_broadcast_round_locked()

    async def _score_and_broadcast_round_locked(self) -> None:
        """Inner scoring logic, must be called under self._scoring_lock."""
        await self._stop_scoring_timeout()
        await self.broadcast(rounds.score_round(self))

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
            self._cancel_game_complete_task()
            self._game_complete_task = _create_logged_task(
                self._broadcast_game_complete_after_delay(),
                name=f"game_complete_{self.room_id}",
            )
            return

        self.start_next_round_timeout(settings.round_results_countdown_seconds)

    async def _broadcast_game_complete_after_delay(self) -> None:
        """Wait for the round-results countdown, then broadcast game_complete."""
        await asyncio.sleep(settings.game_complete_delay_seconds)
        game_complete_event = rounds.game_complete_event(self)
        await self.broadcast(game_complete_event)
        logger.info("[GameRoom %s] Game complete. Winner: %s", self.room_id, game_complete_event.winner)
        await self.persist()

    def start_scoring_timeout(self, timeout_seconds: int) -> None:
        """Start a fallback scoring task in case not all players submit in time."""
        if self._round_scoring_task and not self._round_scoring_task.done():
            self._round_scoring_task.cancel()
        self._round_scoring_task = _create_logged_task(
            self._scoring_timeout(timeout_seconds),
            name=f"scoring_timeout_{self.room_id}",
        )

    def start_guessing_timeout(self, timeout_seconds: int) -> None:
        """Start the drawing->guessing transition timer for the active round."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = _create_logged_task(
            self._start_guessing_after_delay(timeout_seconds),
            name=f"start_guessing_{self.room_id}",
        )

    async def _start_guessing_after_delay(self, timeout_seconds: int) -> None:
        try:
            await asyncio.sleep(timeout_seconds + settings.drawing_to_guessing_buffer_seconds)
            await self.broadcast(
                rounds.start_guessing_event(self),
            )
            await self.persist()
            self.start_scoring_timeout(self.metadata.round_length or 30)
        except asyncio.CancelledError:
            pass

    def start_first_round_timeout(self) -> None:
        """Start the initial game-start delay before round 1 begins."""
        self.start_next_round_timeout(settings.game_start_delay_seconds, round_number=1)

    def start_next_round_timeout(self, timeout_seconds: int, *, round_number: int | None = None) -> None:
        """Schedule the next round to start after a delay."""
        if self._next_round_start_task and not self._next_round_start_task.done():
            self._next_round_start_task.cancel()
        self._next_round_start_task = _create_logged_task(
            self._start_next_round_after_delay(timeout_seconds, round_number=round_number),
            name=f"next_round_{self.room_id}",
        )

    async def _start_next_round_after_delay(self, timeout_seconds: int, *, round_number: int | None = None) -> None:
        try:
            await asyncio.sleep(timeout_seconds)
            await self.start_round_with_server_cards(round_number=round_number)
        except asyncio.CancelledError:
            pass

    async def start_round_with_server_cards(self, *, round_number: int | None = None) -> None:
        """Assign cards server-side, start a round, and broadcast the payload."""
        cards = await self._build_server_round_cards()
        next_round = round_number or (self.metadata.current_round + 1)
        round_start_time = self.start_round(round_number=next_round, cards=cards)
        await self.broadcast(
            StartRoundBroadcastEvent(
                type="start_round",
                round=next_round,
                cards={
                    player_id: PlayerCardPayload.model_validate(card.model_dump())
                    for player_id, card in cards.items()
                },
                roundStartTime=round_start_time,
            ),
        )
        await self.persist()
        self.start_guessing_timeout(self.metadata.round_length or 30)

    async def _build_server_round_cards(self) -> dict[str, PlayerCardState]:
        """Fetch one random category set per player from the category service."""
        if not self.players:
            return {}

        session_maker = get_session_maker()
        async with session_maker() as db:
            response = await category_service.get_random_category_cards(
                db,
                difficulty=self.metadata.difficulty,
                count=1,
                player_count=len(self.players),
                room_id=self.room_id,
                language=self.metadata.language,
            )

        selected_sets = list(response.categories.values())
        player_ids = list(self.players.keys())
        cards: dict[str, PlayerCardState] = {}

        for index, player_id in enumerate(player_ids):
            card_set = selected_sets[index]
            cards[player_id] = PlayerCardState(
                category=card_set.category,
                items=card_set.items,
                alternatives=card_set.alternatives,
                is_custom=card_set.is_custom,
            )

        return cards

    def _cancel_game_complete_task(self) -> None:
        if self._game_complete_task and not self._game_complete_task.done():
            self._game_complete_task.cancel()
        self._game_complete_task = None

    async def _scoring_timeout(self, timeout_seconds: int) -> None:
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

    def start_idle_check(self) -> None:
        """Start periodic idle player check if it is not already running."""
        if self._idle_check_task and not self._idle_check_task.done():
            return
        self._idle_check_task = _create_logged_task(
            self._idle_check_loop(),
            name=f"idle_check_{self.room_id}",
        )

    async def stop_idle_check(self) -> None:
        """Stop idle player check and any pending scoring tasks."""
        await _cancel_task(self._idle_check_task)
        self._idle_check_task = None
        await _cancel_task(self._guessing_start_task)
        self._guessing_start_task = None
        await _cancel_task(self._next_round_start_task)
        self._next_round_start_task = None
        await self._stop_scoring_timeout()
        await _cancel_task(self._game_complete_task)
        self._game_complete_task = None

    async def _idle_check_loop(self) -> None:
        """Periodically check for idle players and cleanup expired votes."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                await self._check_idle_players()
                self.cleanup_expired_votes()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[GameRoom %s] Error in idle check", self.room_id)

    async def _check_idle_players(self) -> None:
        """Check for and disconnect idle players during active game phases."""
        if self.metadata.game_phase not in (LOBBY_PHASE, COMPLETE_PHASE):
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

    async def add_player(self, player_id: str, name: str, websocket: WebSocket) -> tuple[PlayerInfo, bool]:
        """Add a player to the room.

        Returns tuple: (player, is_reconnecting_host)
        Raises ValueError if room is full
        """
        return await player_lifecycle.add_player(
            self,
            player_id,
            name,
            websocket,
            max_players=settings.max_players,
            player_info_factory=PlayerInfo,
        )

    async def remove_player(self, player_id: str) -> None:
        """Remove a player from the room."""
        await player_lifecycle.remove_player(
            self,
            player_id,
            host_transfer_delay_ms=settings.host_transfer_delay_ms,
            schedule_host_transfer=lambda disconnected_host_id: _create_logged_task(
                self._delayed_host_transfer(disconnected_host_id),
                name=f"host_transfer_{self.room_id}",
            ),
        )
        # If a player disconnects during guessing without having submitted, adjust
        # the expected count so scoring can trigger without waiting for the timeout.
        if self.metadata.game_phase == GUESSING_PHASE and player_id not in self.metadata.submitted_players:
            self.metadata.player_count_for_scoring = max(0, self.metadata.player_count_for_scoring - 1)
            expected = self.metadata.player_count_for_scoring
            submitted = len(self.metadata.submitted_players)
            if expected > 0 and submitted >= expected:
                _create_logged_task(
                    self.score_and_broadcast_round(),
                    name=f"auto_score_{self.room_id}",
                )

    async def _delayed_host_transfer(self, old_host_id: str) -> None:
        """Transfer host after a delay, allowing for reconnection."""
        await player_lifecycle.delayed_host_transfer(
            self,
            old_host_id,
            host_transfer_delay_ms=settings.host_transfer_delay_ms,
        )

    def update_player_activity(self, player_id: str) -> None:
        """Update the last activity timestamp for a player."""
        player_lifecycle.update_player_activity(self, player_id)

    def is_host(self, player_id: str | None) -> bool:
        """Return whether the given player currently owns the room."""
        return player_lifecycle.is_host(self, player_id)

    def room_state_event(self) -> RoomStateEvent:
        """Build the canonical websocket room-state snapshot."""
        return RoomStateEvent.model_validate(
            {
                "players": [PlayerSnapshot(id=player.id, name=player.name) for player in self.players.values()],
                "hostId": self.host_id,
                "categories": self.metadata.categories,
                "gamePhase": self.metadata.game_phase,
                "difficulty": self.metadata.difficulty,
                "maxRounds": self.metadata.max_rounds,
                "roundStartTime": self.metadata.round_start_time,
                "roundLength": self.metadata.round_length,
                "padVisibility": self.metadata.pad_visibility,
                "isPrivate": self.metadata.is_private,
                "language": self.metadata.language,
            },
        )

    def configure_game(
        self,
        *,
        round_length: int | None,
        difficulty: Difficulty | None,
        max_rounds: int | None,
    ) -> None:
        """Initialize a new game from the lobby state."""
        rounds.configure_game(
            self,
            round_length=round_length,
            difficulty=difficulty,
            max_rounds=max_rounds,
        )

    def start_round(self, *, round_number: int | None, cards: dict[str, PlayerCardState] | None) -> int:
        """Transition the room into a new drawing round and return the start timestamp."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = None
        if self._next_round_start_task and not self._next_round_start_task.done():
            self._next_round_start_task.cancel()
        self._next_round_start_task = None
        if self._round_scoring_task and not self._round_scoring_task.done():
            self._round_scoring_task.cancel()
        self._round_scoring_task = None
        self._cancel_game_complete_task()
        return rounds.start_round(self, round_number=round_number, cards=cards)

    def start_guessing(self) -> int:
        """Transition into the guessing phase and return the scoring timeout."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = None
        return rounds.start_guessing(self)

    def reset_game(self) -> None:
        """Reset mutable game state back to the lobby."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = None
        if self._round_scoring_task and not self._round_scoring_task.done():
            self._round_scoring_task.cancel()
        self._round_scoring_task = None
        if self._next_round_start_task and not self._next_round_start_task.done():
            self._next_round_start_task.cancel()
        self._next_round_start_task = None
        self._cancel_game_complete_task()
        rounds.reset_game(self)

    async def _stop_scoring_timeout(self) -> None:
        """Cancel any in-flight scoring timeout task."""
        await _cancel_task(self._round_scoring_task)
        self._round_scoring_task = None

    def mark_player_ready(self, player_id: str) -> ReadyStatusEvent:
        """Record that a player is ready and return the shared ready-status payload."""
        return rounds.mark_player_ready(self, player_id)

    async def record_guess_submission(
        self,
        *,
        player_id: str,
        target_player_id: str,
        guesses: list[str],
    ) -> None:
        """Store a guess submission and score immediately when all players are done."""
        if rounds.record_guess_submission(
            self,
            player_id=player_id,
            target_player_id=target_player_id,
            guesses=guesses,
        ):
            await self.score_and_broadcast_round()

    async def broadcast(self, message: WebSocketMessage, exclude: str | None = None) -> None:
        """Broadcast a message to all players in the room."""
        disconnected_players = []

        for player_id, player in self.players.items():
            if exclude and player_id == exclude:
                continue
            try:
                await send_ws_message(player.websocket, message)
            except Exception:
                logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
                disconnected_players.append(player_id)

        if not disconnected_players:
            return

        # Remove all failed players first, then notify remaining players once per removal.
        # Using a direct send loop (not broadcast) avoids re-entrant cleanup if further
        # sends fail during the departure notifications.
        for player_id in disconnected_players:
            await self.remove_player(player_id)

        for player_id in disconnected_players:
            departure = PlayerLeftEvent(playerId=player_id)
            for player in self.players.values():
                with contextlib.suppress(Exception):
                    await send_ws_message(player.websocket, departure)

    async def send_to_player(self, player_id: str, message: WebSocketMessage) -> None:
        """Send a message to a specific player."""
        if player_id in self.players:
            player = self.players[player_id]
            try:
                await send_ws_message(player.websocket, message)
            except Exception:
                logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
                await self.remove_player(player_id)

    def get_player_list(self) -> list[dict[str, str]]:
        """Get the list of all players in the room."""
        return [{"id": p.id, "name": p.name} for p in self.players.values()]

    async def initiate_kick_vote(self, initiator_id: str, target_player_id: str) -> KickVoteResult:
        """Initiate a vote to kick a player.

        Returns a JSON-safe status payload with info about the vote.
        """
        return await kick_vote.initiate_kick_vote(self, initiator_id, target_player_id)

    async def cast_kick_vote(self, voter_id: str, target_player_id: str) -> KickVoteResult:
        """Cast a vote to kick a player."""
        return await kick_vote.cast_kick_vote(self, voter_id, target_player_id)

    def _get_required_votes(self, *, target_is_host: bool) -> int:
        """Calculate required votes to kick a player."""
        return kick_vote.get_required_votes(self, target_is_host=target_is_host)

    async def kick_player(self, player_id: str, reason: str = "Kicked") -> None:
        """Kick a player from the room."""
        await kick_vote.kick_player(self, player_id, reason)

    def cleanup_expired_votes(self) -> int:
        """Remove expired kick votes."""
        return kick_vote.cleanup_expired_votes(self)

    # ------------------------------------------------------------------ #
    # Redis persistence                                                    #
    # ------------------------------------------------------------------ #

    def to_state(self) -> RoomState:
        """Serialize room state to a validated model for Redis storage."""
        return room_lifecycle.to_state(self)

    @classmethod
    def from_state(cls, state: RoomState) -> GameRoom:
        """Restore a room from a Redis-persisted state model (no players reconnect yet)."""
        return room_lifecycle.from_state(state, room_factory=cls, metadata_factory=RoomMetadata)

    async def persist(self) -> None:
        """Write current room state to Redis."""
        await room_lifecycle.persist(self)

    # ------------------------------------------------------------------ #

    def is_empty(self) -> bool:
        """Check if the room is empty."""
        return len(self.players) == 0

    def should_hibernate(self) -> bool:
        """Check if room should be hibernated (empty for < hibernation timeout)."""
        return room_lifecycle.should_hibernate(self)

    def should_be_removed(self) -> bool:
        """Check if room should be permanently removed."""
        return room_lifecycle.should_be_removed(self)

    def get_age_seconds(self) -> float:
        """Get room age in seconds."""
        return room_lifecycle.get_age_seconds(self)

    def get_empty_duration_seconds(self) -> float | None:
        """Get how long room has been empty, or None if not empty."""
        return room_lifecycle.get_empty_duration_seconds(self)

    async def hibernate(self) -> None:
        """Put room into hibernation mode."""
        await room_lifecycle.hibernate(self)

    async def cleanup_custom_categories(self) -> None:
        """Delete all custom categories created for this room."""
        try:
            async with get_session_maker()() as session:
                # Delete all categories with this room_id
                stmt = delete(Category).where(Category.room_id == self.room_id)
                result = await session.execute(stmt)
                await session.commit()

                deleted_count = int(getattr(result, "rowcount", 0) or 0)
                if deleted_count > 0:
                    logger.info("[GameRoom %s] Cleaned up %s custom categories", self.room_id, deleted_count)
        except Exception:
            logger.exception("[GameRoom %s] Error cleaning up custom categories", self.room_id)


class RoomManager:
    """Manages all game rooms with PartyKit-like lifecycle.

    Features:
    - Automatic hibernation of empty rooms after 1 minute
    - Garbage collection of hibernated rooms after 5 minutes
    - Periodic cleanup every 60 seconds
    """

    # Cleanup interval (1 minute)
    CLEANUP_INTERVAL_SECONDS = 60
    room_type = GameRoom
    metadata_type = RoomMetadata

    def __init__(self):
        self.rooms: dict[str, GameRoom] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start the room manager and periodic cleanup."""
        if self._is_running:
            return

        self._is_running = True
        await self._restore_from_redis()
        self._cleanup_task = _create_logged_task(
            self._periodic_cleanup_loop(),
            name="room_manager_cleanup",
        )
        logger.info("[RoomManager] Started with cleanup interval of %ss", self.CLEANUP_INTERVAL_SECONDS)

    async def _restore_from_redis(self) -> None:
        """Load persisted room states from Redis on startup."""
        await room_lifecycle.restore_rooms_from_redis(self)

    async def stop(self) -> None:
        """Stop the room manager and cleanup tasks."""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._cleanup_task

        # Clean up all rooms
        for room_id in list(self.rooms.keys()):
            await self.remove_room(room_id)

        logger.info("[RoomManager] Stopped and cleaned up all rooms")

    async def _periodic_cleanup_loop(self) -> None:
        """Periodically clean up and hibernate rooms."""
        while self._is_running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL_SECONDS)
                await self._run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[RoomManager] Error in cleanup loop")

    async def _run_cleanup(self) -> None:
        """Run cleanup and hibernation checks on all rooms."""
        await room_lifecycle.run_cleanup(self)

    def get_or_create_room(self, room_id: str) -> GameRoom:
        """Get an existing room or create a new one."""
        if room_id not in self.rooms:
            room = GameRoom(room_id)
            self.rooms[room_id] = room
            room.start_idle_check()
            logger.info("[RoomManager] Created new room: %s (total rooms: %s)", room_id, len(self.rooms))
        return self.rooms[room_id]

    def get_room(self, room_id: str) -> GameRoom | None:
        """Get an existing room."""
        return self.rooms.get(room_id)

    async def remove_room(self, room_id: str) -> None:
        """Remove a room and clean up custom categories."""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            await room.stop_idle_check()
            await room.cleanup_custom_categories()  # Clean up custom categories
            del self.rooms[room_id]
            await delete_room_state(room_id)
            logger.info("[RoomManager] Removed room %s (total rooms: %s)", room_id, len(self.rooms))

    def get_stats(self) -> RoomStats:
        """Get room manager statistics."""
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
        """Find a random public room that's available to join.

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
            and room.metadata.game_phase == LOBBY_PHASE
        ]

        return secrets.choice(available_rooms) if available_rooms else None


# Global room manager instance
room_manager = RoomManager()
