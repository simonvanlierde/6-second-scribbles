"""Tests for the FastAPI app surface and core websocket flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

import app.main as main_module
from app.core.types import GamePhase
from app.rooms.manager import room_manager
from tests.helpers import JoinedPlayer, join_player, joined_players, receive_json, send_json

if TYPE_CHECKING:
    from httpx import AsyncClient

fastapi_app = main_module.application

OK_STATUSES = ("ok", "degraded")
SERVICE_NAME = "Six Second Scribbles API"
ROOM_STATUS_PATH = "/api/rooms/{room_id}/status"
ROOM_STATUS_SCHEMA = "RoomStatusResponse"
USER_RESPONSE_SCHEMA = "UserResponse"
LOCALE_AVAILABILITY_SCHEMA = "LocaleAvailabilityItem"
VERSION_KEY = "version"
DATABASE_KEY = "database"
CACHE_KEY = "cache"
ROOM_STATE = "room_state"
MEDIUM = "medium"


def test_root_endpoint(test_client: TestClient) -> None:
    """Health endpoint returns the expected service metadata."""
    response = test_client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in OK_STATUSES  # fakes may not support SELECT 1
    assert payload["service"] == SERVICE_NAME
    assert VERSION_KEY in payload
    assert DATABASE_KEY in payload
    assert CACHE_KEY in payload


def test_openapi_includes_contract_schemas() -> None:
    """OpenAPI includes the contract schemas used by the frontend."""
    spec = fastapi_app.openapi()
    schemas = spec["components"]["schemas"]

    assert ROOM_STATUS_PATH in spec["paths"]
    assert ROOM_STATUS_SCHEMA in schemas
    assert USER_RESPONSE_SCHEMA in schemas
    assert LOCALE_AVAILABILITY_SCHEMA in schemas


async def test_room_status_for_existing_and_missing_room(async_client: AsyncClient) -> None:
    """Room status reports existence for missing and populated rooms."""
    missing_response = await async_client.get("/api/rooms/NONEXISTENT/status")
    assert missing_response.status_code == 200
    assert missing_response.json() == {"exists": False}

    room = room_manager.get_or_create_room("TEST01")
    await room.add_player("player-1", "Alice", AsyncMock())
    room.metadata.game_phase = GamePhase.DRAWING

    existing_response = await async_client.get("/api/rooms/TEST01/status")
    assert existing_response.status_code == 200
    assert existing_response.json() == {"exists": True, "players": 1, "game_phase": GamePhase.DRAWING.value}


def test_join_broadcast_lists_all_players(test_client: TestClient) -> None:
    """Joining broadcasts the same player list to every socket."""
    with joined_players(
        test_client,
        "JOIN01",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "request_game_state", "playerId": "player-1"})
        send_json(ws2, {"type": "request_game_state", "playerId": "player-2"})

        assert receive_json(ws1)["players"] == receive_json(ws2)["players"]


def test_player_disconnect_broadcasts_player_left(test_client: TestClient) -> None:
    """Disconnecting one websocket informs the remaining players."""
    with joined_players(
        test_client,
        "DISC01",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (ws1, ws2):
        ws1.close()

        assert receive_json(ws2) == {"type": "player_left", "playerId": "player-1"}


def test_request_game_state_returns_current_room_state(test_client: TestClient) -> None:
    """Requesting game state returns the current room snapshot."""
    with test_client.websocket_connect("/ws/STATE01") as websocket:
        initial_state = receive_json(websocket)
        assert initial_state["type"] == ROOM_STATE

        join_player(websocket, "player-1", "Alice")
        send_json(websocket, {"type": "request_game_state", "playerId": "player-1"})

        room_state = receive_json(websocket)
        assert room_state["type"] == ROOM_STATE
        assert room_state["players"] == [{"id": "player-1", "name": "Alice", "categories": []}]
        assert room_state["difficulty"] == MEDIUM
        assert room_state["maxRounds"] == 5
        assert room_state["padVisibility"]
        assert not room_state["isPrivate"]


def test_ready_and_restart_messages_are_broadcast(test_client: TestClient) -> None:
    """Readiness and restart events are echoed back through the room."""
    with test_client.websocket_connect("/ws/CONTROL01") as websocket:
        receive_json(websocket)
        join_player(websocket, "player-1", "Alice")

        send_json(websocket, {"type": "player_ready", "playerId": "player-1"})
        ready_status = receive_json(websocket)
        assert ready_status == {"type": "ready_status", "readyCount": 1, "totalPlayers": 1}

        send_json(websocket, {"type": "restart_game"})
        assert receive_json(websocket) == {"type": "restart_game"}


def test_non_host_cannot_restart_game(test_client: TestClient) -> None:
    """Non-host players are rejected when restarting the game."""
    with joined_players(
        test_client,
        "CONTROL02",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (_ws1, ws2):
        send_json(ws2, {"type": "restart_game", "playerId": "player-2"})

        assert receive_json(ws2) == {
            "type": "permission_error",
            "error": "host_only",
            "message": "Only the host can restart the game.",
        }


def test_invalid_json_does_not_close_connection(test_client: TestClient, sample_messages: dict) -> None:
    """Malformed payloads produce a protocol error without closing the socket."""
    with test_client.websocket_connect("/ws/ERROR01") as websocket:
        receive_json(websocket)
        join_player(websocket, "player-123", "Test Player")

        websocket.send_text("not valid json{")
        assert receive_json(websocket) == {
            "type": "protocol_error",
            "error": "invalid_payload",
            "message": "Invalid websocket payload.",
        }
        send_json(websocket, sample_messages["heartbeat"])
        send_json(websocket, {"type": "request_game_state", "playerId": "player-123"})

        assert receive_json(websocket)["type"] == ROOM_STATE


def test_invalid_typed_payload_returns_protocol_error(test_client: TestClient) -> None:
    """Schema-invalid typed payloads produce a protocol error."""
    with joined_players(
        test_client,
        "PROTO01",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (_ws1, ws2):
        send_json(ws2, {"type": "submit_guess", "playerId": "player-2"})

        assert receive_json(ws2) == {
            "type": "protocol_error",
            "error": "invalid_payload",
            "message": "Invalid websocket payload.",
        }


def test_invalid_start_game_difficulty_returns_protocol_error(test_client: TestClient) -> None:
    """Invalid difficulty values are rejected before a game starts."""
    with joined_players(
        test_client,
        "PROTO02",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (_ws1, ws2):
        send_json(ws2, {"type": "start_game", "difficulty": "expert", "rounds": 3, "drawingTimeLimit": 30})

        assert receive_json(ws2) == {
            "type": "protocol_error",
            "error": "invalid_payload",
            "message": "Invalid websocket payload.",
        }


def test_player_ready_requires_matching_connection_identity(test_client: TestClient) -> None:
    """Ready events must come from the websocket that owns the player id."""
    with joined_players(
        test_client,
        "READY01",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (_ws1, ws2):
        send_json(ws2, {"type": "player_ready", "playerId": "player-1"})

        assert receive_json(ws2) == {
            "type": "player_ready_error",
            "error": "invalid_player",
            "message": "Ready updates must match your connection.",
        }
