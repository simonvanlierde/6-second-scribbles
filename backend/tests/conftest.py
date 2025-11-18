"""
Shared test fixtures and configuration
"""
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

from main import app
from game_room import GameRoom, RoomManager, PlayerInfo


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Synchronous test client for FastAPI app"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for FastAPI app"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def room_id() -> str:
    """Sample room ID for tests"""
    return "TEST01"


@pytest.fixture
def player_data() -> dict:
    """Sample player data"""
    return {
        "id": "player-123",
        "name": "Test Player"
    }


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
        "join": {
            "type": "join",
            "playerId": "player-123",
            "name": "Test Player"
        },
        "start_game": {
            "type": "start_game",
            "difficulty": "medium",
            "rounds": 5,
            "roundLength": 60
        },
        "start_round": {
            "type": "start_round",
            "round": 1,
            "cards": {
                "player-1": {
                    "category": "Animals",
                    "items": ["cat", "dog", "bird"]
                }
            }
        },
        "draw_stroke": {
            "type": "draw_stroke",
            "playerId": "player-1",
            "stroke": {
                "color": "#000000",
                "width": 2,
                "points": [{"x": 10, "y": 20}, {"x": 30, "y": 40}]
            }
        },
        "heartbeat": {
            "type": "heartbeat",
            "playerId": "player-1"
        },
        "settings_update": {
            "type": "settings_update",
            "difficulty": "hard",
            "rounds": 7,
            "roundLength": 45
        },
        "player_ready": {
            "type": "player_ready",
            "playerId": "player-1"
        },
        "restart_game": {
            "type": "restart_game"
        }
    }


@pytest.fixture(autouse=True)
def reset_room_manager():
    """Reset the global room manager between tests"""
    from game_room import room_manager
    room_manager.rooms.clear()
    yield
    room_manager.rooms.clear()
