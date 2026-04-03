"""Redis persistence for game room state."""

# spell-checker: ignore setex
import logging

import redis.asyncio as redis

from app.core.config import settings
from app.rooms.state import RoomState

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Get the Redis client instance, creating it if it doesn't exist."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client connection if it exists."""
    global _redis_client  # noqa: PLW0603
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


def _room_key(room_id: str) -> str:
    """Generate a Redis key for storing a room's state based on its ID."""
    return f"room:{room_id}"


async def save_room_state(room_id: str, state: RoomState) -> None:
    """Save the given room state to Redis with a TTL."""
    try:
        r = await get_redis()
        await r.setex(_room_key(room_id), settings.room_ttl_seconds, state.model_dump_json())
    except Exception:
        logger.exception("[Redis] Failed to save room %s", room_id)


async def load_room_state(room_id: str) -> RoomState | None:
    """Load the room state from Redis. Returns None if not found or on error."""
    try:
        r = await get_redis()
        data = await r.get(_room_key(room_id))
        return RoomState.model_validate_json(data) if data else None
    except Exception:
        logger.exception("[Redis] Failed to load room %s", room_id)
        return None


async def delete_room_state(room_id: str) -> None:
    """Delete the room state from Redis. This is called when a room is closed."""
    try:
        r = await get_redis()
        await r.delete(_room_key(room_id))
    except Exception:
        logger.exception("[Redis] Failed to delete room %s", room_id)


async def load_all_room_states() -> list[RoomState]:
    """Load all room states from Redis. This is used on server startup to restore rooms."""
    try:
        r = await get_redis()
        keys = [key async for key in r.scan_iter(match="room:*")]
        if not keys:
            return []
        results = await r.mget(keys)
        return [RoomState.model_validate_json(value) for value in results if value]
    except Exception:
        logger.exception("[Redis] Failed to load all rooms")
        return []
