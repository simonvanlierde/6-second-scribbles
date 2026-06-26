"""Per-room async task scheduler.

Owns all fire-and-forget timers a game room spawns — idle monitoring, the
drawing->guessing transition, scoring fallback, next-round countdown, and
game-complete broadcast — so `GameRoom` can focus on state.

Not owned by the scheduler:
- `_scoring_lock` and `score_and_broadcast_round()` — these live on
  GameRoom because scoring must hold the lock and read multiple room
  fields atomically.
- `_pending_host_transfer` — owned by `player_lifecycle`; it is tied to
  player connection events rather than round phases.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from app.core.config import settings
from app.rooms import rounds

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from app.rooms.manager import GameRoom

logger = logging.getLogger(__name__)

IDLE_CHECK_INTERVAL_SECONDS = 60


def create_logged_task(coroutine: Coroutine[object, object, object], name: str) -> asyncio.Task[object]:
    """Create a fire-and-forget task that logs any unhandled exception."""
    task = asyncio.create_task(coroutine, name=name)
    task.add_done_callback(_log_task_exception)
    return task


async def cancel_task(task: asyncio.Task[object] | None) -> None:
    """Cancel a task and wait for it to finish."""
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


def _log_task_exception(task: asyncio.Task[object]) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("[Task %s] unhandled exception", task.get_name(), exc_info=exc)


SCORING_TIMEOUT_BUFFER_SECONDS = 3


class RoomTaskScheduler:
    """Manages the set of async timers for one `GameRoom`."""

    def __init__(self, room: GameRoom) -> None:
        self._room = room
        self._idle_check_task: asyncio.Task[object] | None = None
        self._guessing_start_task: asyncio.Task[object] | None = None
        self._next_round_start_task: asyncio.Task[object] | None = None
        self._round_scoring_task: asyncio.Task[object] | None = None
        self._game_complete_task: asyncio.Task[object] | None = None

    # ---------- Introspection ----------

    def is_next_round_pending(self) -> bool:
        """Return whether a next-round start timer is currently scheduled."""
        return self._next_round_start_task is not None and not self._next_round_start_task.done()

    # ---------- Idle monitoring ----------

    def start_idle_check(self) -> None:
        """Start the periodic idle-player check loop if it is not already running."""
        if self._idle_check_task and not self._idle_check_task.done():
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return

        self._idle_check_task = create_logged_task(
            self._idle_check_loop(),
            name=f"idle_check_{self._room.room_id}",
        )

    async def shutdown(self) -> None:
        """Cancel every task this scheduler owns and await their teardown."""
        await cancel_task(self._idle_check_task)
        self._idle_check_task = None
        await cancel_task(self._guessing_start_task)
        self._guessing_start_task = None
        await cancel_task(self._next_round_start_task)
        self._next_round_start_task = None
        await cancel_task(self._round_scoring_task)
        self._round_scoring_task = None
        await cancel_task(self._game_complete_task)
        self._game_complete_task = None

    async def _idle_check_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                await self._room.check_idle_players()
                self._room.cleanup_expired_votes()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("[GameRoom %s] Error in idle check", self._room.room_id)

    # ---------- Round-phase timers ----------

    def schedule_guessing_start(self, drawing_time_limit_seconds: int) -> None:
        """Schedule the drawing->guessing transition for the active round."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = create_logged_task(
            self._start_guessing_after_delay(drawing_time_limit_seconds),
            name=f"start_guessing_{self._room.room_id}",
        )

    async def _start_guessing_after_delay(self, drawing_time_limit_seconds: int) -> None:
        try:
            await asyncio.sleep(drawing_time_limit_seconds + settings.drawing_to_guessing_buffer_seconds)
            guessing_event = rounds.start_guessing_event(self._room)
            await self._room.broadcast(guessing_event)
            await self._room.persist()
            self.schedule_scoring_timeout(self._room.metadata.guessing_time_limit or 60)
        except asyncio.CancelledError:
            pass

    def schedule_first_round(self) -> None:
        """Schedule round 1 after the initial game-start delay."""
        if self._next_round_start_task and not self._next_round_start_task.done():
            return
        self.schedule_next_round(settings.game_start_delay_seconds, round_number=1)

    def schedule_next_round(self, timeout_seconds: int, *, round_number: int | None = None) -> None:
        """Schedule the next round to start after a delay."""
        if self._next_round_start_task and not self._next_round_start_task.done():
            self._next_round_start_task.cancel()
        self._next_round_start_task = create_logged_task(
            self._start_next_round_after_delay(timeout_seconds, round_number=round_number),
            name=f"next_round_{self._room.room_id}",
        )

    async def _start_next_round_after_delay(
        self,
        timeout_seconds: int,
        *,
        round_number: int | None = None,
    ) -> None:
        try:
            await asyncio.sleep(timeout_seconds)
            await self._room.start_round_with_server_cards(round_number=round_number)
        except asyncio.CancelledError:
            pass

    def schedule_scoring_timeout(self, timeout_seconds: int) -> None:
        """Schedule a fallback scoring task in case not all players submit in time."""
        if self._round_scoring_task and not self._round_scoring_task.done():
            self._round_scoring_task.cancel()
        self._round_scoring_task = create_logged_task(
            self._scoring_timeout(timeout_seconds),
            name=f"scoring_timeout_{self._room.room_id}",
        )

    async def _scoring_timeout(self, timeout_seconds: int) -> None:
        try:
            await asyncio.sleep(timeout_seconds + SCORING_TIMEOUT_BUFFER_SECONDS)
            logger.info(
                "[GameRoom %s] Scoring timeout: %s/%s players submitted. Scoring now.",
                self._room.room_id,
                len(self._room.metadata.submitted_players),
                self._room.metadata.player_count_for_scoring,
            )
            await self._room.score_and_broadcast_round()
        except asyncio.CancelledError:
            pass

    def schedule_game_complete(self) -> None:
        """Schedule the game_complete broadcast after the final-round countdown."""
        self.cancel_game_complete()
        self._game_complete_task = create_logged_task(
            self._broadcast_game_complete_after_delay(),
            name=f"game_complete_{self._room.room_id}",
        )

    async def _broadcast_game_complete_after_delay(self) -> None:
        await asyncio.sleep(settings.game_complete_delay_seconds)
        event = rounds.game_complete_event(self._room)
        await self._room.broadcast(event)
        logger.info("[GameRoom %s] Game complete. Winner: %s", self._room.room_id, event.winner)
        await self._room.persist()

    # ---------- Cancellation helpers ----------

    async def cancel_scoring_timeout(self) -> None:
        """Cancel any in-flight scoring timeout task."""
        await cancel_task(self._round_scoring_task)
        self._round_scoring_task = None

    def cancel_guessing_start(self) -> None:
        """Cancel any pending drawing->guessing transition task."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = None

    def cancel_game_complete(self) -> None:
        """Cancel any pending game-complete broadcast task."""
        if self._game_complete_task and not self._game_complete_task.done():
            self._game_complete_task.cancel()
        self._game_complete_task = None

    def cancel_round_tasks(self) -> None:
        """Cancel every round-phase timer before starting a new round or resetting."""
        if self._guessing_start_task and not self._guessing_start_task.done():
            self._guessing_start_task.cancel()
        self._guessing_start_task = None
        if self._next_round_start_task and not self._next_round_start_task.done():
            self._next_round_start_task.cancel()
        self._next_round_start_task = None
        if self._round_scoring_task and not self._round_scoring_task.done():
            self._round_scoring_task.cancel()
        self._round_scoring_task = None
        self.cancel_game_complete()
