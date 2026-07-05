"""Redis persistence for game room state."""

# spell-checker: ignore setex
import asyncio
import hashlib
import json
import logging
import secrets
import sys
from typing import TYPE_CHECKING, cast

import redis.asyncio as redis

from app.core.config import settings
from app.rooms.state import RoomState

if TYPE_CHECKING:
    from collections.abc import Awaitable

_PERSISTENCE_ERRORS = (redis.RedisError, asyncio.TimeoutError, ValueError, TypeError)

logger = logging.getLogger(__name__)


class _RedisState:
    """Holds lazily created Redis client."""

    client: redis.Redis | None = None


_state = _RedisState()


async def get_redis() -> redis.Redis:
    """Get the Redis client instance, creating it if it doesn't exist."""
    if _state.client is None:
        _state.client = redis.from_url(settings.redis_url, decode_responses=True)
    return _state.client


async def close_redis() -> None:
    """Close the Redis client connection if it exists."""
    if _state.client is not None:
        await _state.client.aclose()
        _state.client = None


def _room_key(room_id: str) -> str:
    """Generate a Redis key for storing a room's state based on its ID."""
    return f"room:{room_id}"


def _session_key(session_id: str) -> str:
    """Generate a Redis key for a server-side auth session."""
    return f"session:{session_id}"


def _rate_limit_key(bucket: str, identifier: str) -> str:
    """Generate a Redis key for a fixed-window rate limit bucket."""
    return f"rate_limit:{bucket}:{identifier}"


def _category_locale_availability_key(difficulty: str | None) -> str:
    """Generate a Redis key for cached categories locale-availability payload."""
    suffix = (difficulty or "all").lower()
    return f"category_locale_availability:{suffix}"


async def save_room_state(room_id: str, state: RoomState) -> None:
    """Save the given room state to Redis with a TTL."""
    try:
        r = await get_redis()
        await r.setex(_room_key(room_id), settings.room_ttl_seconds, state.model_dump_json())
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to save room %s", room_id)


async def load_room_state(room_id: str) -> RoomState | None:
    """Load the room state from Redis. Returns None if not found or on error."""
    try:
        r = await get_redis()
        data = await r.get(_room_key(room_id))
        return RoomState.model_validate_json(data) if data else None
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to load room %s", room_id)
        return None


async def delete_room_state(room_id: str) -> None:
    """Delete the room state from Redis. This is called when a room is closed."""
    try:
        r = await get_redis()
        await r.delete(_room_key(room_id))
    except _PERSISTENCE_ERRORS:
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
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to load all rooms")
        return []


async def create_session(user_id: str) -> str:
    """Create a new auth session and return its session id."""
    session_id = secrets.token_urlsafe(32)
    try:
        r = await get_redis()
        await r.setex(_session_key(session_id), settings.auth_session_ttl_seconds, user_id)
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to create session for user %s", user_id)
        raise
    return session_id


async def get_session_user_id(session_id: str) -> str | None:
    """Return the user id for an existing auth session."""
    try:
        r = await get_redis()
        # redis-py's async stubs type get() via the shared sync signature, so the
        # awaited value needs a cast to satisfy the type checker.
        return cast("str | None", await r.get(_session_key(session_id)))
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to read session %s", session_id)
        return None


async def delete_session(session_id: str) -> None:
    """Delete a server-side auth session if it exists."""
    try:
        r = await get_redis()
        await r.delete(_session_key(session_id))
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to delete session %s", session_id)


async def increment_rate_limit(bucket: str, identifier: str, *, window_seconds: int) -> tuple[int, int]:
    """Increment a fixed-window rate limit counter and return count plus retry-after seconds."""
    try:
        r = await get_redis()
        key = _rate_limit_key(bucket, identifier)
        # redis-py's async incr() is typed via the sync signature (returns int, not
        # Awaitable[int]); cast so the await type-checks.
        count = await cast("Awaitable[int]", r.incr(key))
        if count == 1:
            await r.expire(key, window_seconds)
        ttl = await r.ttl(key)
        retry_after = max(int(ttl), 0)
        return int(count), retry_after
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to increment rate limit %s for %s", bucket, identifier)
        # Fail closed: if Redis is unavailable we cannot count attempts, so treat
        # the request as over-limit rather than silently disabling every throttle
        # (login/register/room-creation) during the outage. Availability trade-off:
        # a Redis blip 429s these endpoints, but Redis backs sessions/persistence
        # too, so the app is already degraded.
        return sys.maxsize, window_seconds


def _cat_targets_key(category_id: int, locale: str, prompt_ids: list[int]) -> str:
    """Generate a Redis key for localized scoring targets cache.

    The prompt-id subset is part of the key: the same category+locale can be
    requested with different prompt subsets, and each yields different targets.
    Omitting it caused collisions where players were scored against the wrong words.
    """
    digest = hashlib.sha1(",".join(map(str, sorted(prompt_ids))).encode()).hexdigest()[:16]  # noqa: S324
    return f"cat_targets:{category_id}:{locale}:{digest}"


async def cache_localized_scoring_targets(category_id: int, locale: str, prompt_ids: list[int], data: dict) -> None:
    """Cache the localized scoring targets dictionary for 24 hours."""
    try:
        r = await get_redis()
        await r.setex(
            _cat_targets_key(category_id, locale, prompt_ids),
            settings.category_cache_ttl_seconds,
            json.dumps(data),
        )
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to cache scoring targets for %s locale %s", category_id, locale)


async def get_cached_localized_scoring_targets(category_id: int, locale: str, prompt_ids: list[int]) -> dict | None:
    """Load cached localized scoring targets dictionary from Redis."""
    try:
        r = await get_redis()
        data = await r.get(_cat_targets_key(category_id, locale, prompt_ids))
        return json.loads(data) if data else None
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to load cached scoring targets for %s locale %s", category_id, locale)
        return None


async def cache_category_locale_availability(difficulty: str | None, items: list[dict]) -> None:
    """Cache locale-availability endpoint payload."""
    try:
        r = await get_redis()
        payload = json.dumps(items, separators=(",", ":"))
        await r.setex(
            _category_locale_availability_key(difficulty),
            settings.category_locale_availability_ttl_seconds,
            payload,
        )
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to cache locale availability for difficulty=%s", difficulty)


async def get_cached_category_locale_availability(difficulty: str | None) -> list[dict] | None:
    """Load cached locale-availability endpoint payload."""
    try:
        r = await get_redis()
        raw = await r.get(_category_locale_availability_key(difficulty))
        if not raw:
            return None
        payload = json.loads(raw)
        return payload if isinstance(payload, list) else None
    except _PERSISTENCE_ERRORS:
        logger.exception("[Redis] Failed to load locale availability cache for difficulty=%s", difficulty)
        return None
