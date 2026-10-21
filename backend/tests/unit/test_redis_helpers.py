"""Focused coverage for Redis helpers."""
# spell-checker: ignore setex

from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from redis.exceptions import RedisError

from app.core import redis as redis_module
from app.rooms.state import RoomState

if TYPE_CHECKING:
    import pytest

ROOM_SCAN_PATTERN = "room:*"
ROOM_KEY_PREFIX = "room:"
ROOM_ID = "ROOM01"
USER_ID = "user-1"
LEAKY_SESSION_ID = "secret-session-id"
CACHE_WRITE_FAILED_LOG = "Failed to cache cat_targets:1:en:"


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.expirations[key] = ttl

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def scan_iter(self, *, match: str) -> object:
        for key in list(self.store):
            if match == ROOM_SCAN_PATTERN and key.startswith(ROOM_KEY_PREFIX):
                yield key

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [self.store.get(key) for key in keys]

    async def incr(self, key: str) -> int:
        next_value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(next_value)
        return next_value

    async def expire(self, key: str, ttl: int, *, nx: bool = False) -> bool:
        if nx and key in self.expirations:
            return False
        self.expirations[key] = ttl
        return True

    async def ttl(self, key: str) -> int:
        return self.expirations.get(key, -1)

    def pipeline(self, *, transaction: bool = True) -> _FakePipeline:
        del transaction
        return _FakePipeline(self)


class _FakePipeline:
    """Minimal MULTI/EXEC stand-in: queue commands, run them on execute()."""

    def __init__(self, backend: _FakeRedis) -> None:
        self._backend = backend
        self._ops: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def incr(self, key: str) -> _FakePipeline:
        self._ops.append(("incr", (key,), {}))
        return self

    def expire(self, key: str, ttl: int, *, nx: bool = False) -> _FakePipeline:
        self._ops.append(("expire", (key, ttl), {"nx": nx}))
        return self

    async def execute(self) -> list[object]:
        return [await getattr(self._backend, name)(*args, **kwargs) for name, args, kwargs in self._ops]


async def test_room_state_and_session_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Room state and sessions round-trip through Redis helpers."""
    fake_redis = _FakeRedis()
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(return_value=fake_redis))
    monkeypatch.setattr(redis_module.secrets, "token_urlsafe", lambda _n: "session-token")

    state = RoomState(room_id=ROOM_ID)
    await redis_module.save_room_state(ROOM_ID, state)
    loaded = RoomState.model_validate_json(fake_redis.store[f"room:{ROOM_ID}"])

    session_id = await redis_module.create_session(USER_ID)
    session_user = await redis_module.get_session_user_id(session_id)

    assert loaded is not None
    assert loaded.room_id == ROOM_ID
    assert session_user == USER_ID


async def test_load_all_room_states_and_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loading all rooms and fixed-window rate limiting use the expected Redis keys."""
    fake_redis = _FakeRedis()
    fake_redis.store["room:ROOM01"] = RoomState(room_id="ROOM01").model_dump_json()
    fake_redis.store["room:ROOM02"] = RoomState(room_id="ROOM02").model_dump_json()
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(return_value=fake_redis))

    states = await redis_module.load_all_room_states()
    first_count, retry_after = await redis_module.increment_rate_limit("auth_guest", "127.0.0.1", window_seconds=30)

    assert sorted(state.room_id for state in states) == ["ROOM01", "ROOM02"]
    assert first_count == 1
    assert retry_after == 30


async def test_load_all_room_states_skips_an_unreadable_room(monkeypatch: pytest.MonkeyPatch) -> None:
    """A room saved in another schema is skipped; the readable rooms still load."""
    fake_redis = _FakeRedis()
    fake_redis.store["room:ROOM01"] = RoomState(room_id="ROOM01").model_dump_json()
    fake_redis.store["room:OLD01"] = '{"room_id": "OLD01", "field_from_another_version": 1}'
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(return_value=fake_redis))

    states = await redis_module.load_all_room_states()

    assert [state.room_id for state in states] == ["ROOM01"]


async def test_session_errors_do_not_log_the_session_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A session id is a login credential, so a Redis failure must not write it to the logs."""
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(side_effect=RedisError("boom")))

    await redis_module.get_session_user_id(LEAKY_SESSION_ID)

    assert LEAKY_SESSION_ID not in caplog.text


async def test_redis_helpers_fall_back_cleanly_on_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error paths log and return safe defaults."""
    failing = AsyncMock(side_effect=RedisError("boom"))
    monkeypatch.setattr(redis_module, "get_redis", failing)

    assert await redis_module.load_all_room_states() == []
    assert await redis_module.get_session_user_id("session-1") is None
    # Rate limiting fails CLOSED: an un-countable request is reported as over-limit
    # so a Redis outage cannot silently disable every throttle.
    count, retry_after = await redis_module.increment_rate_limit("auth", "id", window_seconds=10)
    assert count == sys.maxsize
    assert retry_after == 10
    assert await redis_module.get_cached_localized_scoring_targets(1, "en", [1]) is None
    assert await redis_module.get_cached_category_locale_availability(None) is None


async def test_failed_cache_write_is_logged_not_raised(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Scoring still runs when Redis cannot store the targets; only the cache entry is lost."""
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(side_effect=RedisError("boom")))

    await redis_module.cache_localized_scoring_targets(1, "en", [1], {"cat": ["cat"]})

    assert CACHE_WRITE_FAILED_LOG in caplog.text
