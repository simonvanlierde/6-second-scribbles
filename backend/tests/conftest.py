"""Shared test fixtures and configuration.

Uses testcontainers for real PostgreSQL and Redis instances during tests.
"""

from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.game_room import GameRoom, RoomManager


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:18-alpine", driver="asyncpg") as pg:
        yield pg


@pytest.fixture(scope="session")
def redis_container():
    """Start a Redis container for the test session."""
    with RedisContainer("redis:8-alpine") as redis:
        yield redis


@pytest.fixture(autouse=True)
def _configure_db(postgres_container, redis_container, monkeypatch):
    """Point the app at the test containers for every test.

    Patches module-level engine and session_maker so all code paths
    (lifespan, test_db fixture, cleanup_custom_categories, etc.) use the
    containerised database without needing a running event loop here.
    """
    import app.database as db_mod
    import app.redis_store as redis_mod
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    db_url = postgres_container.get_connection_url()
    redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setattr(db_mod, "DATABASE_URL", db_url)
    monkeypatch.setattr(redis_mod, "REDIS_URL", redis_url)

    engine = create_async_engine(db_url, echo=False, future=True, pool_pre_ping=True, pool_size=5, max_overflow=10)
    session_maker = async_sessionmaker(
        engine,
        class_=db_mod.AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "async_session_maker", session_maker)

    redis_mod._redis_client = None


@pytest.fixture
def test_client() -> Generator[TestClient]:
    """Synchronous test client for FastAPI app with real containers."""
    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient]:
    """Async test client for FastAPI app"""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def room_id() -> str:
    """Sample room ID for tests"""
    return "TEST01"


@pytest.fixture
def player_data() -> dict:
    """Sample player data"""
    return {"id": "player-123", "name": "Test Player"}


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
async def game_room(room_id: str) -> GameRoom:
    """Create a fresh game room for testing"""
    room = GameRoom(room_id)
    await room.start_idle_check()
    yield room
    await room.stop_idle_check()


@pytest.fixture
async def room_with_players(game_room: GameRoom, mock_websocket) -> GameRoom:
    """Game room with two players already joined"""
    ws1 = AsyncMock()
    ws1.send_text = AsyncMock()
    ws2 = AsyncMock()
    ws2.send_text = AsyncMock()

    await game_room.add_player("player-1", "Alice", ws1)
    await game_room.add_player("player-2", "Bob", ws2)

    return game_room


@pytest.fixture
def room_manager() -> RoomManager:
    """Fresh room manager instance"""
    return RoomManager()


@pytest.fixture
def sample_messages() -> dict:
    """Collection of sample game messages"""
    return {
        "join": {"type": "join", "playerId": "player-123", "name": "Test Player"},
        "start_game": {"type": "start_game", "difficulty": "medium", "rounds": 5, "roundLength": 60},
        "start_round": {
            "type": "start_round",
            "round": 1,
            "cards": {"player-1": {"category": "Animals", "items": ["cat", "dog", "bird"]}},
        },
        "draw_stroke": {
            "type": "draw_stroke",
            "playerId": "player-1",
            "stroke": {"color": "#000000", "width": 2, "points": [{"x": 10, "y": 20}, {"x": 30, "y": 40}]},
        },
        "heartbeat": {"type": "heartbeat", "playerId": "player-1"},
        "settings_update": {"type": "settings_update", "difficulty": "hard", "rounds": 7, "roundLength": 45},
        "player_ready": {"type": "player_ready", "playerId": "player-1"},
        "restart_game": {"type": "restart_game"},
    }


@pytest.fixture(autouse=True)
def reset_room_manager():
    """Reset the global room manager between tests"""
    from app.game_room import room_manager

    room_manager.rooms.clear()
    yield
    room_manager.rooms.clear()
