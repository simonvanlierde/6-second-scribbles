"""Redis persistence for game room state.

Rooms are serialized to Redis on every state change and restored on server startup.
TTL matches the hibernation timeout (5 minutes) so abandoned rooms expire automatically.
"""

# spell-checker: ignore setex
import json
import logging

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


def _room_key(room_id: str) -> str:
    return f"room:{room_id}"


async def save_room_state(room_id: str, state: dict) -> None:
    try:
        r = await get_redis()
        await r.setex(_room_key(room_id), settings.room_ttl_seconds, json.dumps(state))
    except Exception:
        logger.exception("[Redis] Failed to save room %s", room_id)


async def load_room_state(room_id: str) -> dict | None:
    try:
        r = await get_redis()
        data = await r.get(_room_key(room_id))
        return json.loads(data) if data else None
    except Exception:
        logger.exception("[Redis] Failed to load room %s", room_id)
        return None


async def delete_room_state(room_id: str) -> None:
    try:
        r = await get_redis()
        await r.delete(_room_key(room_id))
    except Exception:
        logger.exception("[Redis] Failed to delete room %s", room_id)


async def load_all_room_states() -> list[dict]:
    try:
        r = await get_redis()
        keys = [key async for key in r.scan_iter(match="room:*")]
        if not keys:
            return []
        results = await r.mget(keys)
        return [json.loads(v) for v in results if v]
    except Exception:
        logger.exception("[Redis] Failed to load all rooms")
        return []
