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
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException

from app.categories import service as category_service
from app.core.config import settings
from app.core.database import get_session_maker
from app.core.redis import delete_room_state, load_all_room_states, save_room_state
from app.core.types import (
    GamePhase,
    LanguageCode,
)
from app.rooms import kick_vote, player_lifecycle, rounds
from app.rooms.player_lifecycle import PlayerInfo
from app.rooms.protocol import (
    DrawStrokeBatchServerEvent,
    DrawStrokePayload,
    GalleryDrawingPayload,
    PlayerCardPayload,
    PlayerSnapshot,
    RestartGameEvent,
    RoomStateEvent,
    StartRoundServerEvent,
    StrokeDelta,
    StrokeFragment,
    WebSocketMessage,
    encode_ws_message,
)
from app.rooms.scheduler import RoomTaskScheduler, create_logged_task
from app.rooms.state import (
    PlayerPromptAssignmentState,
    RoomMetadataState,
    RoomState,
)

# spell-checker: ignore reconnections

if TYPE_CHECKING:
    from fastapi import WebSocket

    from app.rooms.kick_vote import KickVote

logger = logging.getLogger(__name__)

# Cap on retained shared-lobby-doodle strokes, so a long-lived lobby can't grow
# the in-memory stroke list without bound. Oldest strokes are trimmed past this.
MAX_LOBBY_STROKES = 500
# Cap on points within a single reconstructed stroke. Without this, a client that
# opens one stroke and then only ever sends continuation fragments (never a new
# strokeStart) would extend that one stroke forever — MAX_LOBBY_STROKES bounds the
# count of strokes, not points inside one. Generous vs any real freehand stroke.
MAX_STROKE_POINTS = 4000
# Cap on points across the whole doodle. The two caps above still allow 500 x 4000
# points, a room_state of tens of MB that freezes the single worker to build.
MAX_LOBBY_POINTS = 20_000
# Lobby doodle fragments are held this long and sent as one draw_stroke_batch: a
# drawing client sends 20 a second, and relaying each alone made server CPU grow
# with fragments x players.
LOBBY_FRAGMENT_TICK_SECONDS = 0.05


class RoomCapacityError(Exception):
    """Raised when the global room cap is reached and a new room cannot be created."""


class ClientRoomLimitError(RoomCapacityError):
    """Raised when one client already holds its share of open rooms."""


@dataclass(frozen=True)
class RoomStats:
    """Aggregate room manager statistics."""

    total_rooms: int
    active_rooms: int
    hibernated_rooms: int
    empty_rooms: int
    total_players: int


async def _close_quietly(websocket: WebSocket) -> None:
    with contextlib.suppress(Exception):
        await websocket.close(code=1011)


class GameRoom:
    """Manages a single game room with multiple players."""

    def __init__(self, room_id: str):
        self.room_id = room_id
        # Network that opened the room, for the per-client room cap. In-memory only.
        self.creator: str | None = None
        self.players: dict[str, PlayerInfo] = {}
        # Spectator sockets: they get every broadcast but never a card, and do not
        # count as players. In-memory only; a spectator re-sends watch on reconnect.
        self.observers: list[PlayerInfo] = []
        self.host_id: str | None = None
        self.metadata = RoomMetadataState()
        self.scheduler = RoomTaskScheduler(self)
        self.pending_host_transfer: asyncio.Task[object] | None = None
        self._scoring_lock = asyncio.Lock()
        self.last_host_id: str | None = None  # Track last host for reconnection
        self.last_host_user_id: str | None = None  # Authenticated owner of last host, for reclaim checks
        self.created_at = time.time()
        # When the room last had no connected players. A new room starts empty,
        # so one that nobody ever joins still expires after the TTL.
        self.emptied_at: float | None = self.created_at
        self.is_hibernated = False
        self.active_kick_votes: dict[str, KickVote] = {}  # target_player_id -> KickVote
        # Player ids and accounts voted out of this room; add_player refuses them.
        # In-memory only: a restart forgives, and a cleared browser gets a new id.
        self.kicked_ids: set[str] = set()
        # Latest drawing PNG (data URL) per player for the current round. Kept in
        # memory only (deliberately not in the Redis-persisted RoomState) so
        # reconnecting players can recover drawings without bloating persistence.
        self.round_drawings: dict[str, str] = {}
        # Completed drawings for every scored round, for the end-of-game gallery.
        # In-memory only (like round_drawings); rehydrated to clients via room_state.
        self.drawing_history: list[GalleryDrawingPayload] = []
        # Server-authoritative strokes of the shared lobby drawpad, reconstructed
        # from the partials clients already relay, so late joiners/reconnects
        # hydrate the doodle via room_state. In-memory only, like round_drawings.
        self.lobby_strokes: list[DrawStrokePayload] = []
        self._lobby_partial_index: dict[str, int] = {}
        # Points across lobby_strokes, kept up to date on every change: summing them on
        # every relayed fragment cost O(strokes) on the hottest path.
        self._lobby_points = 0
        self._pending_fragments: list[StrokeFragment] = []
        self._fragment_flush: asyncio.TimerHandle | None = None

    async def score_and_broadcast_round(self) -> None:
        """Score submitted guesses with fuzzy matching and broadcast round_complete."""
        async with self._scoring_lock:
            await self._score_and_broadcast_round_locked()

    async def _score_and_broadcast_round_locked(self) -> None:
        """Inner scoring logic, must be called under self._scoring_lock."""
        # Idempotent: scoring can be triggered from several places (all-submitted,
        # disconnect/remove, the scoring timeout). If two land close together the
        # lock serializes them; bail on the second so the round is not scored twice.
        if self.metadata.game_phase != GamePhase.GUESSING:
            return
        await self.scheduler.cancel_scoring_timeout()
        session_maker = get_session_maker()
        try:
            async with session_maker() as db:
                round_complete_event = await rounds.score_round(self, db)
        except Exception:
            # The scoring timeout is already cancelled, so an escape here would strand
            # the room in GUESSING. End the round without points instead.
            logger.exception("[GameRoom %s] Scoring failed, ending the round without points", self.room_id)
            round_complete_event = rounds.no_points_round_event(self)

        # Snapshot this round's drawings into the end-of-game gallery before the
        # next round clears round_drawings, so reconnecting clients can recover it.
        for player_id, drawing in self.round_drawings.items():
            player = self.players.get(player_id)
            self.drawing_history.append(
                GalleryDrawingPayload(
                    round=self.metadata.current_round,
                    playerId=player_id,
                    name=player.name if player else "",
                    color=player.color if player else None,
                    drawing=drawing,
                ),
            )

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
        round_start_time = rounds.start_round(self, round_number=next_round, cards=assignments)
        await self.send_round_start(
            next_round,
            {
                player_id: PlayerCardPayload.model_validate(assignment.model_dump())
                for player_id, assignment in assignments.items()
            },
            round_start_time,
        )
        await self.persist()
        self.scheduler.schedule_guessing_start(self.metadata.drawing_time_limit or 30)

    async def _build_server_round_assignments(self) -> dict[str, PlayerPromptAssignmentState]:
        """Pick one category per player, then deal each player its card in their own locale."""
        if not self.players:
            return {}

        player_ids = list(self.players)
        async with get_session_maker()() as db:
            category_ids = await category_service.select_category_ids(
                db,
                difficulty=self.metadata.difficulty,
                player_count=len(player_ids),
                locales=[self.get_player_locale(player_id) for player_id in player_ids],
                room_locale=self.metadata.default_locale,
            )
            # Reuse categories when fewer are available than there are players.
            return {
                player_id: await category_service.deal_category(
                    db,
                    category_id=category_ids[index % len(category_ids)],
                    preferred_locale=self.get_player_locale(player_id),
                    fallback_locale=self.metadata.default_locale,
                )
                for index, player_id in enumerate(player_ids)
            }

    async def restart_game(self) -> None:
        """Send the room back to the lobby after a finished game."""
        rounds.reset_game(self)
        # Players who dropped during the finished game and never returned are cleared
        # as we go back to the lobby (they were kept through final results).
        await player_lifecycle.prune_disconnected(self)
        await self.broadcast(RestartGameEvent(type="restart_game"))
        await self.persist()

    async def check_idle_players(self) -> None:
        """Drop expired kick votes, and disconnect idle players during active game phases."""
        kick_vote.cleanup_expired_votes(self)
        if self.metadata.game_phase not in (GamePhase.LOBBY, GamePhase.FINAL_RESULTS):
            now = time.time()
            idle_players = []

            for player_id, player in self.players.items():
                if not player.connected:
                    continue  # already dropped; kept as a 'reconnecting' presence
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

    def add_observer(self, websocket: WebSocket) -> bool:
        """Register a spectator socket; return False when the room has no spectator seats left."""
        if len(self.observers) >= settings.max_observers:
            return False
        self.observers.append(PlayerInfo(id="observer", name="observer", websocket=websocket))
        return True

    def remove_observer(self, websocket: WebSocket) -> None:
        """Forget a spectator socket."""
        self.observers = [observer for observer in self.observers if observer.websocket is not websocket]

    def apply_lobby_partial(self, player_id: str, stroke: StrokeDelta, *, is_start: bool) -> None:
        """Fold a relayed stroke fragment into the authoritative lobby doodle.

        Mirrors the client's applyPartialStroke: a start (or an unknown player)
        opens a new stroke; later fragments extend that player's in-progress one.
        """
        idx = self._lobby_partial_index.get(player_id)
        if is_start or idx is None or idx >= len(self.lobby_strokes):
            self.lobby_strokes.append(
                DrawStrokePayload(color=stroke.color, width=stroke.width, points=list(stroke.points))
            )
            self._lobby_points += len(stroke.points)
            self._lobby_partial_index[player_id] = len(self.lobby_strokes) - 1
        else:
            # Bound points per stroke too: a client that keeps sending continuation
            # fragments without a new strokeStart would grow one stroke unbounded.
            room = MAX_STROKE_POINTS - len(self.lobby_strokes[idx].points)
            if room > 0:
                added = stroke.points[:room]
                self.lobby_strokes[idx].points.extend(added)
                self._lobby_points += len(added)
        # NOTE: bound the shared doodle by stroke count and total points so a
        # marathon lobby can't grow unbounded; the oldest strokes go first.
        drop = max(0, len(self.lobby_strokes) - MAX_LOBBY_STROKES)
        total = self._lobby_points - sum(len(s.points) for s in self.lobby_strokes[:drop])
        while total > MAX_LOBBY_POINTS and drop < len(self.lobby_strokes) - 1:
            total -= len(self.lobby_strokes[drop].points)
            drop += 1
        if drop:
            self._trim_lobby_strokes(drop)

    def _trim_lobby_strokes(self, drop: int) -> None:
        """Drop the oldest `drop` strokes, keeping in-progress strokes attached to theirs."""
        self._lobby_points -= sum(len(s.points) for s in self.lobby_strokes[:drop])
        self.lobby_strokes = self.lobby_strokes[drop:]
        self._lobby_partial_index = {pid: i - drop for pid, i in self._lobby_partial_index.items() if i >= drop}

    def clear_lobby_strokes(self) -> None:
        """Reset the shared lobby doodle (host clear, or leaving the lobby)."""
        self.lobby_strokes.clear()
        self._lobby_partial_index.clear()
        self._lobby_points = 0
        # Fragments still waiting for the tick belong to the doodle just cleared.
        self._pending_fragments.clear()

    def queue_lobby_fragment(self, fragment: StrokeFragment) -> None:
        """Hold a doodle fragment for the next tick, when the room's fragments go out together."""
        self._pending_fragments.append(fragment)
        if self._fragment_flush is None:
            self._fragment_flush = asyncio.get_running_loop().call_later(
                LOBBY_FRAGMENT_TICK_SECONDS, self._flush_lobby_fragments
            )

    def _flush_lobby_fragments(self) -> None:
        self._fragment_flush = None
        fragments, self._pending_fragments = self._pending_fragments, []
        if fragments:
            event = DrawStrokeBatchServerEvent(fragments=fragments)
            create_logged_task(self.broadcast(event), name=f"fragments_{self.room_id}")

    def room_state_event(self, *, for_player_id: str | None = None) -> RoomStateEvent:
        """Build the canonical websocket room-state snapshot.

        When ``for_player_id`` is given and that player has a card for the active
        round, include it so a reconnecting client can restore its prompt.
        """
        assignment = self.metadata.player_assignments.get(for_player_id) if for_player_id else None
        card = PlayerCardPayload.model_validate(assignment.model_dump()) if assignment else None
        return RoomStateEvent.model_validate(
            {
                "players": self.get_player_list(),
                "hostId": self.host_id,
                "gamePhase": self.metadata.game_phase,
                "difficulty": self.metadata.difficulty,
                "currentRound": self.metadata.current_round,
                "maxRounds": self.metadata.max_rounds,
                "roundStartTime": self.metadata.round_start_time,
                "guessingStartTime": self.metadata.guessing_start_time,
                "drawingTimeLimit": self.metadata.drawing_time_limit,
                "guessingTimeLimit": self.metadata.guessing_time_limit,
                "guessTargets": self.metadata.guess_targets,
                "drawings": self.round_drawings,
                "drawingHistory": self.drawing_history,
                "lobbyStrokes": self.lobby_strokes,
                "card": card,
                "readyCount": len(self.metadata.ready_players),
                "totalPlayers": len(self.players),
                "padVisibility": self.metadata.pad_visibility,
                "isPrivate": self.metadata.is_private,
                "defaultLocale": self.metadata.default_locale,
            },
        )

    def get_player_locale(self, player_id: str, *, fallback_locale: LanguageCode | None = None) -> LanguageCode:
        """Resolve the effective locale for a connected player."""
        return self.metadata.player_locales.get(player_id, fallback_locale or self.metadata.default_locale)

    def get_player_user_id(self, player_id: str) -> str | None:
        """Return the authenticated user id associated with a player connection, if any."""
        return self.metadata.player_user_ids.get(player_id)

    async def enter_guessing(self) -> None:
        """Move from drawing to guessing, tell everyone, and arm the scoring timeout.

        Runs from the drawing timer or early, once every connected player is ready.
        """
        self.scheduler.cancel_guessing_start()
        timeout_seconds = rounds.start_guessing(self)
        await self.broadcast(rounds.guessing_event_payload(self))
        await self.persist()
        self.scheduler.schedule_scoring_timeout(timeout_seconds)

    async def broadcast(self, message: WebSocketMessage, exclude: str | None = None) -> None:
        """Broadcast a message to all connected players in the room."""
        # Every recipient gets the same text, so serialize once: per-recipient
        # serialization made relay work grow with players squared.
        text = encode_ws_message(message)
        # Snapshot: send_text awaits, and a concurrent remove/disconnect
        # mutating self.players mid-iteration would raise "dict changed size".
        players = [player for player_id, player in list(self.players.items()) if player_id != exclude]
        await self._deliver_all([*players, *self.observers], text)

    async def _deliver_to_observers(self, text: str) -> None:
        await self._deliver_all(list(self.observers), text)

    async def _deliver_all(self, recipients: list[PlayerInfo], text: str) -> None:
        """Send text to each still-connected recipient, dropping any whose send fails or stalls."""
        pending = iter(recipients)
        while True:
            player: PlayerInfo | None = None
            try:
                # One timer for the whole loop rather than one per send: arming a timer
                # per recipient was a measurable share of the CPU per relayed stroke.
                async with asyncio.timeout(settings.ws_send_timeout_seconds):
                    for player in pending:
                        if not player.connected:
                            continue
                        try:
                            await player.websocket.send_text(text)
                        except Exception:
                            logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
                            self._drop(player)
                    return
            except TimeoutError:
                # The send that ran out the clock is the stuck one; the rest get a new timer.
                if player is not None:
                    logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
                    self._drop(player)

    async def _deliver(self, player: PlayerInfo, text: str) -> None:
        try:
            # A client that stops reading would otherwise hold this await, and with
            # it every broadcast and timer in the room.
            await asyncio.wait_for(player.websocket.send_text(text), settings.ws_send_timeout_seconds)
        except Exception:
            logger.exception("[GameRoom %s] Error sending to %s", self.room_id, player.name)
            self._drop(player)

    def _drop(self, player: PlayerInfo) -> None:
        # A failed send on a still-"connected" socket means we missed the
        # close. Mark them disconnected so we stop trying; the websocket's
        # receive loop will raise next and run disconnect_player, which
        # broadcasts presence and handles host/scoring/cleanup.
        player.connected = False
        # Close so the client reconnects instead of sitting on a socket that gets
        # nothing; in the background, because a stuck socket may not close quickly.
        create_logged_task(_close_quietly(player.websocket), name=f"close_{self.room_id}_{player.id}")

    async def send_round_start(
        self,
        round_number: int | None,
        cards: dict[str, PlayerCardPayload],
        round_start_time: int,
    ) -> None:
        """Send each connected player a start_round holding only their own card.

        A broadcast would hand every player everyone's prompts. A player who is
        offline now gets their card from room_state when they reconnect.
        Spectators get the same event with no cards.
        """
        for player_id, player in list(self.players.items()):
            if not player.connected:
                continue
            own = {player_id: cards[player_id]} if player_id in cards else {}
            event = StartRoundServerEvent(round=round_number, cards=own, roundStartTime=round_start_time)
            await self._deliver(player, encode_ws_message(event))
        if self.observers:
            event = StartRoundServerEvent(round=round_number, cards={}, roundStartTime=round_start_time)
            await self._deliver_to_observers(encode_ws_message(event))

    def _ordered_players(self) -> list[PlayerInfo]:
        """Players in stable seat order (insertion order for any without a seat)."""
        seats = self.metadata.player_seats
        return sorted(self.players.values(), key=lambda p: seats.get(p.id, len(seats)))

    def get_player_list(self) -> list[PlayerSnapshot]:
        """Get the list of all players in the room, in stable seat order."""
        return [
            PlayerSnapshot(id=p.id, name=p.name, color=p.color, connected=p.connected) for p in self._ordered_players()
        ]

    # ------------------------------------------------------------------ #
    # Redis persistence                                                    #
    # ------------------------------------------------------------------ #

    def to_state(self) -> RoomState:
        """Serialize room state to a validated model for Redis storage."""
        return RoomState(
            room_id=self.room_id,
            host_id=self.host_id,
            last_host_id=self.last_host_id,
            created_at=self.created_at,
            emptied_at=self.emptied_at,
            is_hibernated=self.is_hibernated,
            metadata=self.metadata,
        )

    @classmethod
    def from_state(cls, state: RoomState) -> GameRoom:
        """Restore a room from a Redis-persisted state model (no players reconnect yet)."""
        room = cls(state.room_id)
        room.host_id = state.host_id
        room.last_host_id = state.last_host_id
        room.created_at = state.created_at
        # Restored rooms have no connected players yet; start their empty clock now
        # if the saved state had players, or the room would never expire.
        room.emptied_at = state.emptied_at or time.time()
        room.is_hibernated = state.is_hibernated
        room.metadata = state.metadata.model_copy(deep=True)
        return room

    async def persist(self) -> None:
        """Write current room state to Redis."""
        await save_room_state(self.room_id, self.to_state())

    # ------------------------------------------------------------------ #

    def is_empty(self) -> bool:
        """Whether the room has no connected players.

        A room holding only disconnected ("reconnecting") players counts as empty
        so the hibernation/TTL cleanup can reclaim it if nobody returns.
        """
        return not any(player.connected for player in self.players.values())

    def _empty_for(self, seconds: int) -> bool:
        """Whether the room has had no connected player for at least `seconds`."""
        return self.is_empty() and self.emptied_at is not None and time.time() - self.emptied_at >= seconds

    def should_hibernate(self) -> bool:
        """Check if room should be hibernated after being empty long enough."""
        return not self.is_hibernated and self._empty_for(settings.room_hibernation_delay_seconds)

    def should_be_removed(self) -> bool:
        """Check if room should be permanently removed after its TTL expires."""
        return self._empty_for(settings.room_ttl_seconds)

    def hibernate(self) -> None:
        """Put an empty room into hibernation mode."""
        if self.is_hibernated or not self.is_empty():
            return
        logger.info("[GameRoom %s] Entering hibernation mode (age: %.0fs)", self.room_id, time.time() - self.created_at)
        self.is_hibernated = True


class RoomManager:
    """Manages all game rooms.

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
        states = await load_all_room_states()
        for state in states:
            room = GameRoom.from_state(state)
            self.rooms[state.room_id] = room
            room.scheduler.start_idle_check()
        if states:
            logger.info("[RoomManager] Restored %s room(s) from Redis", len(states))

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
                await self.run_cleanup()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[RoomManager] Error in cleanup loop")

    async def run_cleanup(self) -> tuple[int, int]:
        """Hibernate rooms empty for a while, remove those past their TTL; return both counts."""
        total_rooms = len(self.rooms)
        to_remove = [room_id for room_id, room in self.rooms.items() if room.should_be_removed()]
        to_hibernate = [
            room for room in self.rooms.values() if room.room_id not in to_remove and room.should_hibernate()
        ]

        for room in to_hibernate:
            room.hibernate()
        for room_id in to_remove:
            await self.remove_room(room_id)

        if to_hibernate or to_remove:
            logger.info(
                "[RoomManager] Cleanup: %s total, %s hibernated, %s removed",
                total_rooms,
                len(to_hibernate),
                len(to_remove),
            )
        return len(to_hibernate), len(to_remove)

    def get_or_create_room(self, room_id: str, *, creator: str | None = None) -> GameRoom:
        """Get an existing room or create a new one.

        Raises ``RoomCapacityError`` when a *new* room would exceed the global
        cap, and ``ClientRoomLimitError`` when ``creator`` already opened
        ``max_rooms_per_client`` rooms that are still open, so one client cannot
        fill the global cap. Existing rooms are always returned.
        """
        if room_id not in self.rooms:
            if len(self.rooms) >= settings.max_total_rooms:
                msg = f"Global room cap reached (maximum {settings.max_total_rooms} rooms)"
                raise RoomCapacityError(msg)
            if creator is not None:
                held = sum(1 for room in self.rooms.values() if room.creator == creator)
                if held >= settings.max_rooms_per_client:
                    msg = f"Client room cap reached (maximum {settings.max_rooms_per_client} rooms)"
                    raise ClientRoomLimitError(msg)
            room = GameRoom(room_id)
            room.creator = creator
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
        - Not refusing newcomers with seats_busy

        Returns room_id if found, None otherwise
        """
        available_rooms = [
            room_id
            for room_id, room in self.rooms.items()
            if not room.metadata.is_private
            and 0 < len(room.players) < max_players
            and room.metadata.game_phase == GamePhase.LOBBY
            and not player_lifecycle.seats_busy(room)
        ]

        return secrets.choice(available_rooms) if available_rooms else None


# Global room manager instance
room_manager = RoomManager()
