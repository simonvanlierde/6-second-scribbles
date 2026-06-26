"""Fast fixtures for unit and app-level backend tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

import app.main as main_module
from app.categories import service as category_service
from app.core import database
from app.core import redis as redis_module
from app.rooms.manager import GameRoom, RoomManager
from app.rooms.scheduler import create_logged_task
from tests.constants import (
    MEDIUM,
    PLAYER_ONE_ID,
    PLAYER_ONE_NAME,
    PLAYER_TWO_ID,
    PLAYER_TWO_NAME,
    START_GAME,
    START_ROUND,
    TEST_ROOM_ID,
)
from tests.support import TestWebSocket, as_websocket

if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import AsyncGenerator, Callable, Generator

fastapi_app = main_module.application


class _RoomHarness:
    room_id: str


class _GuessingSchedulerHarness:
    _guessing_start_task: Task[object] | None
    _room: _RoomHarness

    async def _start_guessing_after_delay(self, delay_seconds: int) -> None: ...


@pytest.fixture
def room_id() -> str:
    """Sample room ID for tests."""
    return TEST_ROOM_ID


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Fake Redis client for fast tests."""
    return FakeRedis(decode_responses=True)


@pytest.fixture(autouse=True)
async def configure_unit_services(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: FakeRedis,
) -> AsyncGenerator[None]:
    """Wire the app to fake Redis and keep infra teardown local to the test."""

    async def fake_get_redis() -> FakeRedis:
        return fake_redis

    async def fake_close_redis() -> None:
        await fake_redis.aclose()

    async def fake_close_db() -> None:
        return None

    monkeypatch.setattr(redis_module, "get_redis", fake_get_redis)
    monkeypatch.setattr(redis_module, "close_redis", fake_close_redis)
    monkeypatch.setattr(main_module, "get_redis", fake_get_redis)
    monkeypatch.setattr(main_module, "close_redis", fake_close_redis)
    monkeypatch.setattr(database, "close_db", fake_close_db)
    monkeypatch.setattr(main_module, "close_db", fake_close_db)

    fastapi_app.dependency_overrides.clear()
    yield
    fastapi_app.dependency_overrides.clear()
    await fake_redis.aclose()


@pytest.fixture
def test_client() -> Generator[TestClient]:
    """Synchronous test client for app-level fast tests."""
    with TestClient(fastapi_app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient]:
    """Async test client for app-level fast tests."""
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_websocket() -> TestWebSocket:
    """Lightweight websocket for GameRoom unit tests."""
    return TestWebSocket()


@pytest.fixture
def make_ws() -> Callable[..., TestWebSocket]:
    """Factory that creates lightweight websocket test doubles."""

    def _factory(*, send_error: Exception | None = None) -> TestWebSocket:
        return TestWebSocket(send_error=send_error)

    return _factory


@pytest.fixture
async def game_room(room_id: str) -> AsyncGenerator[GameRoom]:
    """Create a fresh game room for testing."""
    room = GameRoom(room_id)
    room.scheduler.start_idle_check()
    yield room
    await room.scheduler.shutdown()


@pytest.fixture
async def room_with_players(game_room: GameRoom) -> GameRoom:
    """Game room with two players already joined."""
    ws1 = TestWebSocket()
    ws2 = TestWebSocket()

    await game_room.add_player(PLAYER_ONE_ID, PLAYER_ONE_NAME, as_websocket(ws1))
    await game_room.add_player(PLAYER_TWO_ID, PLAYER_TWO_NAME, as_websocket(ws2))

    return game_room


@pytest.fixture
def _deterministic_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make random.sample deterministic by taking the first N items."""
    monkeypatch.setattr(category_service.random, "sample", lambda items, n: list(items)[:n])


@pytest.fixture
def room_manager() -> RoomManager:
    """Fresh room manager instance."""
    return RoomManager()


@pytest.fixture
async def managed_room_manager() -> AsyncGenerator[RoomManager]:
    """RoomManager with lifecycle management."""
    manager = RoomManager()
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def sample_messages() -> dict[str, object]:
    """Collection of sample game messages."""
    return {
        "join": {"type": "join", "playerId": "player-123", "name": "Test Player"},
        START_GAME: {"type": START_GAME, "difficulty": MEDIUM, "rounds": 5, "drawingTimeLimit": 60},
        "start_round": {
            "type": START_ROUND,
            "round": 1,
            "Prompts": {PLAYER_ONE_ID: {"category": "Animals", "items": ["cat", "dog", "bird"]}},
        },
        "draw_stroke": {
            "type": "draw_stroke",
            "playerId": PLAYER_ONE_ID,
            "stroke": {"color": "#000000", "width": 2, "points": [{"x": 10, "y": 20}, {"x": 30, "y": 40}]},
        },
        "heartbeat": {"type": "heartbeat", "playerId": PLAYER_ONE_ID},
        "settings_update": {"type": "settings_update", "difficulty": "hard", "rounds": 7, "drawingTimeLimit": 45},
        "player_ready": {"type": "player_ready", "playerId": PLAYER_ONE_ID},
        "restart_game": {"type": "restart_game"},
    }


@pytest.fixture
def immediate_guessing_transition(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the drawing-to-guessing timer to fire immediately in tests."""

    def schedule_immediately(self: _GuessingSchedulerHarness, _drawing_time_limit_seconds: int) -> None:
        task = getattr(self, "_guessing_start_task", None)
        if task is not None and not task.done():
            task.cancel()
        self._guessing_start_task = create_logged_task(
            self._start_guessing_after_delay(0),  # type: ignore[attr-defined]
            name=f"start_guessing_{self._room.room_id}",  # type: ignore[attr-defined]
        )

    monkeypatch.setattr("app.rooms.scheduler.RoomTaskScheduler.schedule_guessing_start", schedule_immediately)
