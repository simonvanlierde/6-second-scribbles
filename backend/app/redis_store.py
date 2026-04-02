"""Redis persistence for game room state.

Rooms are serialized to Redis on every state change and restored on server startup.
TTL matches the hibernation timeout (5 minutes) so abandoned rooms expire automatically.
"""

# spell-checker: ignore setex
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import redis.asyncio as redis

from app.config import settings
from app.room_state import RoomState

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI


@dataclass
class _AppBinding:
    """Holds the FastAPI app used by Redis helpers."""

    app: FastAPI | None = None


_binding = _AppBinding()


def bind_app(app: FastAPI) -> None:
    """Bind the FastAPI app used to store the shared Redis client."""
    _binding.app = app


def _require_app() -> FastAPI:
    if _binding.app is None:
        msg = "Redis store has not been bound to a FastAPI app."
        raise RuntimeError(msg)
    return _binding.app


def _get_app_client(app: FastAPI) -> redis.Redis | None:
    return cast("redis.Redis | None", getattr(app.state, "redis_client", None))


async def get_redis() -> redis.Redis:
    """Get the Redis client instance, creating it if it doesn't exist."""
    app = _require_app()
    client = _get_app_client(app)
    if client is None:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        app.state.redis_client = client
    return client


async def close_redis() -> None:
    """Close the Redis client connection if it exists."""
    app = _require_app()
    client = _get_app_client(app)
    if client:
        await client.aclose()
    app.state.redis_client = None


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
