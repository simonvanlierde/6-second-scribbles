"""Game Room Manager for Six Second Scribbles.

Architecture: server-driven room and game orchestration.
- Server owns room state, card assignment, phase transitions, scoring, and completion
- Clients render server state and send user actions
- Server broadcasts room, round, and scoring state to all clients

Concurrency model: all room state mutations happen on the single FastAPI
asyncio event loop and rely on the Python GIL for atomicity of individual
dict/set/list operations. The only explicit lock is `_scoring_lock`, which
serializes `score_and_broadcast_round()` because that method must read
multiple metadata fields atomically (assignments, submissions, scores).
Horizontally scaling the backend would require Redis-backed locks — not
needed today.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.categories import service as category_service
from app.core.config import settings
from app.core.database import get_session_maker
from app.core.redis import delete_room_state
from app.core.types import (
    GamePhase,
    LanguageCode,
)
from app.rooms import kick_vote, player_lifecycle, rounds
from app.rooms import lifecycle as room_lifecycle
from app.rooms.protocol import (
    PlayerCardPayload,
    PlayerLeftEvent,
    PlayerListItem,
    PlayerSnapshot,
    ReadyStatusEvent,
    RoomStateEvent,
    StartRoundServerEvent,
    WebSocketMessage,
    send_ws_message,
)
from app.rooms.scheduler import RoomTaskScheduler, create_logged_task
from app.rooms.state import (
    PlayerPromptAssignmentState,
    RoomMetadataState,
)

# spell-checker: ignore reconnections

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.rooms.kick_vote import KickVote
    from app.rooms.results import KickVoteResult
    from app.rooms.state import RoomState

logger = logging.getLogger(__name__)


class RoomCapacityError(Exception):
    """Raised when the global room cap is reached and a new room cannot be created."""


@dataclass
class PlayerInfo:
    """Information about a player in a game room."""

    id: str
    name: str
    websocket: WebSocket
    last_activity: float = field(default_factory=time.time)
    color: str | None = None


@dataclass(frozen=True)
class RoomStats:
    """Aggregate room manager statistics."""

    total_rooms: int
    active_rooms: int
    hibernated_rooms: int
    empty_rooms: int
    total_players: int


class GameRoom:
    """Manages a single game room with multiple players."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.players: dict[str, PlayerInfo] = {}
        self.host_id: str | None = None
        self.metadata = RoomMetadataState()
        self.scheduler = RoomTaskScheduler(self)
        self.pending_host_transfer: asyncio.Task[object] | None = None
        self._scoring_lock = asyncio.Lock()
        self.last_host_id: str | None = None  # Track last host for reconnection
        self.created_at = time.time()
        self.last_activity = time.time()
        self.emptied_at: float | None = None  # When room became empty
        self.is_hibernated = False
        self.active_kick_votes: dict[str, KickVote] = {}  # target_player_id -> KickVote

    async def score_and_broadcast_round(self) -> None:
        """Score submitted guesses with fuzzy matching and broadcast round_complete."""
        async with self._scoring_lock:
            await self._score_and_broadcast_round_locked()

    async def _score_and_broadcast_round_locked(self) -> None:
        """Inner scoring logic, must be called under self._scoring_lock."""
        await self.scheduler.cancel_scoring_timeout()
        session_maker = get_session_maker()
        async with session_maker() as db:
            round_complete_event = await rounds.score_round(self, db)
        await self.broadcast(round_complete_event)

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
            self.scheduler.schedule_game_complete()
            return

        self.scheduler.schedule_next_round(settings.round_results_countdown_seconds)

    async def start_round_with_server_cards(self, *, round_number: int | None = None) -> None:
        """Assign prompts server-side, start a round, and broadcast the payload."""
        try:
            assignments = await self._build_server_round_assignments()
        except HTTPException as exc:
            logger.warning(
                "[GameRoom %s] Unable to start round %s with server prompts: %s",
                self.room_id,
                round_number or (self.metadata.current_round + 1),
                exc,
            )
            await self.broadcast(self.room_state_event())
            await self.persist()
            return
        next_round = round_number or (self.metadata.current_round + 1)
        round_start_time = self.start_round(round_number=next_round, cards=assignments)
        await self.broadcast(
            StartRoundServerEvent(
                type="start_round",
                round=next_round,
                cards={
                    player_id: PlayerCardPayload.model_validate(assignment.model_dump())
                    for player_id, assignment in assignments.items()
                },
                roundStartTime=round_start_time,
            ),
        )
        await self.persist()
        self.scheduler.schedule_guessing_start(self.metadata.drawing_time_limit or 30)

    async def _build_server_round_assignments(self) -> dict[str, PlayerPromptAssignmentState]:
        """Fetch one canonical category per player, then localize it per player."""
        if not self.players:
            return {}

        player_ids = list(self.players.keys())
        participant_locales = [self.get_player_locale(player_id) for player_id in player_ids]

        session_maker = get_session_maker()
        async with session_maker() as db:
            response = await category_service.select_category_sets(
                db,
                difficulty=self.metadata.difficulty,
                count=1,
                player_count=len(player_ids),
                locale=self.metadata.default_locale,
                locales=participant_locales,
            )

        selected_sets = response.selections
        assignments: dict[str, PlayerPromptAssignmentState] = {}

        async with session_maker() as db:
            for index, player_id in enumerate(player_ids):
                selected_category = selected_sets[index]
                localized_category = await category_service.get_localized_category_set(
                    db,
                    category_id=selected_category.category_id,
                    preferred_locale=self.get_player_locale(player_id),
                    fallback_locale=self.metadata.default_locale,
                )
                assignments[player_id] = PlayerPromptAssignmentState(
                    category_id=localized_category.category_id,
                    category=localized_category.category_name,
                    item_ids=localized_category.item_ids,
                    items=localized_category.items,
                    alternatives=localized_category.alternatives,
                )

        return assignments

    async def check_idle_players(self) -> None:
        """Check for and disconnect idle players during active game phases."""
        if self.metadata.game_phase not in (GamePhase.LOBBY, GamePhase.FINAL_RESULTS):
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

    async def add_player(
        self,
        player_id: str,
        name: str,
        websocket: WebSocket,
        *,
        preferred_locale: LanguageCode | None = None,
        user_id: str | None = None,
        preferred_color: str | None = None,
    ) -> tuple[PlayerInfo, bool]:
        """Add a player to the room.

        Returns tuple: (player, is_reconnecting_host)
        Raises ValueError if room is full
        """
        return await player_lifecycle.add_player(
            self,
            player_id,
            name,
            websocket,
            preferred_locale=preferred_locale,
            user_id=user_id,
            preferred_color=preferred_color,
            max_players=settings.max_players,
            player_info_factory=PlayerInfo,
        )

    async def remove_player(self, player_id: str) -> None:
        """Remove a player from the room."""
        await player_lifecycle.remove_player(
            self,
            player_id,
            host_transfer_delay_ms=settings.host_transfer_delay_ms,
            schedule_host_transfer=lambda disconnected_host_id: create_logged_task(
                self._delayed_host_transfer(disconnected_host_id),
                name=f"host_transfer_{self.room_id}",
            ),
        )
        # If a player disconnects during guessing without having submitted, adjust
        # the expected count so scoring can trigger without waiting for the timeout.
        if self.metadata.game_phase == GamePhase.GUESSING and player_id not in self.metadata.submitted_players:
            self.metadata.player_count_for_scoring = max(0, self.metadata.player_count_for_scoring - 1)
            expected = self.metadata.player_count_for_scoring
            submitted = len(self.metadata.submitted_players)
            if expected > 0 and submitted >= expected:
                create_logged_task(
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
                "players": [
                    PlayerSnapshot(id=player.id, name=player.name, color=player.color)
                    for player in self.players.values()
                ],
                "hostId": self.host_id,
                "categories": self.metadata.categories,
                "gamePhase": self.metadata.game_phase,
                "difficulty": self.metadata.difficulty,
                "maxRounds": self.metadata.max_rounds,
                "roundStartTime": self.metadata.round_start_time,
                "guessingStartTime": self.metadata.guessing_start_time,
                "drawingTimeLimit": self.metadata.drawing_time_limit,
                "guessingTimeLimit": self.metadata.guessing_time_limit,
                "guessTargets": self.metadata.guess_targets,
                "padVisibility": self.metadata.pad_visibility,
                "isPrivate": self.metadata.is_private,
                "defaultLocale": self.metadata.default_locale,
                "customCategoryIds": self.metadata.custom_category_ids,
            },
        )

    def get_player_locale(self, player_id: str, *, fallback_locale: LanguageCode | None = None) -> LanguageCode:
        """Resolve the effective locale for a connected player."""
        return self.metadata.player_locales.get(player_id, fallback_locale or self.metadata.default_locale)

    def get_player_user_id(self, player_id: str) -> str | None:
        """Return the authenticated user id associated with a player connection, if any."""
        return self.metadata.player_user_ids.get(player_id)

    def get_host_owner_user_id(self) -> str | None:
        """Return the current host's authenticated user id, if the host has one."""
        if self.host_id is None:
            return None
        return self.get_player_user_id(self.host_id)

    def start_round(self, *, round_number: int | None, cards: dict[str, PlayerPromptAssignmentState] | None) -> int:
        """Transition the room into a new drawing round and return the start timestamp."""
        self.scheduler.cancel_round_tasks()
        return rounds.start_round(self, round_number=round_number, cards=cards)

    def start_guessing(self) -> int:
        """Transition into the guessing phase and return the scoring timeout."""
        self.scheduler.cancel_guessing_start()
        return rounds.start_guessing(self)

    def reset_game(self) -> None:
        """Reset mutable game state back to the lobby."""
        self.scheduler.cancel_round_tasks()
        rounds.reset_game(self)

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

    def get_player_list(self) -> list[PlayerListItem]:
        """Get the list of all players in the room."""
        return [PlayerListItem(id=p.id, name=p.name, color=p.color) for p in self.players.values()]

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
        return room_lifecycle.from_state(state, room_factory=cls)

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


class RoomManager:
    """Manages all game rooms.

    Features:
    - Automatic hibernation of empty rooms after 1 minute
    - Garbage collection of hibernated rooms after 5 minutes
    - Periodic cleanup every 60 seconds
    """

    # Cleanup interval (1 minute)
    CLEANUP_INTERVAL_SECONDS = 60
    room_type = GameRoom

    def __init__(self):
        self.rooms: dict[str, GameRoom] = {}
        self._cleanup_task: asyncio.Task | None = None
        self.is_running = False

    async def start(self) -> None:
        """Start the room manager and periodic cleanup."""
        if self.is_running:
            return

        self.is_running = True
        await self._restore_from_redis()
        self._cleanup_task = create_logged_task(
            self._periodic_cleanup_loop(),
            name="room_manager_cleanup",
        )
        logger.info("[RoomManager] Started with cleanup interval of %ss", self.CLEANUP_INTERVAL_SECONDS)

    async def _restore_from_redis(self) -> None:
        """Load persisted room states from Redis on startup."""
        await room_lifecycle.restore_rooms_from_redis(self)

    async def stop(self) -> None:
        """Stop the room manager and cleanup tasks."""
        self.is_running = False

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
        while self.is_running:
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
        """Get an existing room or create a new one.

        Raises ``RoomCapacityError`` when a *new* room would exceed the global
        cap. Existing rooms are always returned.
        """
        if room_id not in self.rooms:
            if len(self.rooms) >= settings.max_total_rooms:
                msg = f"Global room cap reached (maximum {settings.max_total_rooms} rooms)"
                raise RoomCapacityError(msg)
            room = GameRoom(room_id)
            self.rooms[room_id] = room
            room.scheduler.start_idle_check()
            logger.info("[RoomManager] Created new room: %s (total rooms: %s)", room_id, len(self.rooms))
        return self.rooms[room_id]

    def get_room(self, room_id: str) -> GameRoom | None:
        """Get an existing room."""
        return self.rooms.get(room_id)

    async def remove_room(self, room_id: str) -> None:
        """Remove a room and clean up its background resources."""
        if room_id in self.rooms:
            room = self.rooms[room_id]
            await room.scheduler.shutdown()
            del self.rooms[room_id]
            await delete_room_state(room_id)
            logger.info("[RoomManager] Removed room %s (total rooms: %s)", room_id, len(self.rooms))

    def get_stats(self) -> RoomStats:
        """Get room manager statistics."""
        total_rooms = len(self.rooms)
        active_rooms = sum(1 for room in self.rooms.values() if not room.is_empty())
        hibernated_rooms = sum(1 for room in self.rooms.values() if room.is_hibernated)
        total_players = sum(len(room.players) for room in self.rooms.values())

        return RoomStats(
            total_rooms=total_rooms,
            active_rooms=active_rooms,
            hibernated_rooms=hibernated_rooms,
            empty_rooms=total_rooms - active_rooms - hibernated_rooms,
            total_players=total_players,
        )

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
            and room.metadata.game_phase == GamePhase.LOBBY
        ]

        return secrets.choice(available_rooms) if available_rooms else None


# Global room manager instance
room_manager = RoomManager()
