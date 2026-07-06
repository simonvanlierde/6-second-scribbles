"""Room persistence and hibernation helpers."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.redis import load_all_room_states, save_room_state
from app.rooms.state import RoomState

if TYPE_CHECKING:
    from app.rooms.manager import GameRoom, RoomManager

logger = logging.getLogger(__name__)


def to_state(room: GameRoom) -> RoomState:
    """Serialize room state to a validated model for Redis storage."""
    return RoomState(
        room_id=room.room_id,
        host_id=room.host_id,
        last_host_id=room.last_host_id,
        created_at=room.created_at,
        emptied_at=room.emptied_at,
        is_hibernated=room.is_hibernated,
        metadata=room.metadata,
    )


def from_state(state: RoomState, *, room_factory: type[GameRoom]) -> GameRoom:
    """Restore a room from a Redis-persisted state model without any connected players."""
    room = room_factory(state.room_id)
    room.host_id = state.host_id
    room.last_host_id = state.last_host_id
    room.created_at = state.created_at
    room.emptied_at = state.emptied_at
    room.is_hibernated = state.is_hibernated
    room.metadata = state.metadata.model_copy(deep=True)
    return room


async def persist(room: GameRoom) -> None:
    """Write current room state to Redis."""
    await save_room_state(room.room_id, to_state(room))


def should_hibernate(room: GameRoom) -> bool:
    """Check if room should be hibernated after being empty long enough."""
    if not room.is_empty() or room.is_hibernated:
        return False

    if room.emptied_at is None:
        return False

    return time.time() - room.emptied_at >= settings.room_hibernation_delay_seconds


def should_be_removed(room: GameRoom) -> bool:
    """Check if room should be permanently removed after its TTL expires."""
    if not room.is_empty():
        return False

    if room.emptied_at is None:
        return False

    return time.time() - room.emptied_at >= settings.room_ttl_seconds


def get_age_seconds(room: GameRoom) -> float:
    """Get room age in seconds."""
    return time.time() - room.created_at


def hibernate(room: GameRoom) -> None:
    """Put an empty room into hibernation mode."""
    if room.is_hibernated or not room.is_empty():
        return

    logger.info("[GameRoom %s] Entering hibernation mode (age: %.0fs)", room.room_id, get_age_seconds(room))
    room.is_hibernated = True


async def restore_rooms_from_redis(manager: RoomManager) -> int:
    """Load persisted room states from Redis on startup."""
    states = await load_all_room_states()
    for state in states:
        room = from_state(state, room_factory=type(manager).room_type)
        manager.rooms[state.room_id] = room
        room.scheduler.start_idle_check()
    if states:
        logger.info("[RoomManager] Restored %s room(s) from Redis", len(states))
    return len(states)


async def run_cleanup(manager: RoomManager) -> tuple[int, int]:
    """Run hibernation and removal checks across all managed rooms."""
    total_rooms = len(manager.rooms)
    hibernated_count = 0
    removed_count = 0

    rooms_to_remove: list[str] = []
    rooms_to_hibernate: list[GameRoom] = []

    for room_id, room in list(manager.rooms.items()):
        if should_be_removed(room):
            rooms_to_remove.append(room_id)
        elif should_hibernate(room):
            rooms_to_hibernate.append(room)

    for room in rooms_to_hibernate:
        hibernate(room)
        hibernated_count += 1

    for room_id in rooms_to_remove:
        await manager.remove_room(room_id)
        removed_count += 1

    if hibernated_count > 0 or removed_count > 0:
        logger.info(
            "[RoomManager] Cleanup: %s total, %s hibernated, %s removed",
            total_rooms,
            hibernated_count,
            removed_count,
        )

    return hibernated_count, removed_count
