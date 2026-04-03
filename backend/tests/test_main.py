"""Tests for the FastAPI app surface and core websocket flows."""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.rooms.manager import room_manager
from tests.helpers import JoinedPlayer, join_player, joined_players, receive_json, send_json


def test_root_endpoint(test_client) -> None:
    response = test_client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "Six Second Scribbles API"
    assert "version" in payload


async def test_room_status_for_existing_and_missing_room(async_client) -> None:
    missing_response = await async_client.get("/rooms/NONEXISTENT/status")
    assert missing_response.status_code == 200
    assert missing_response.json() == {"exists": False}

    room = room_manager.get_or_create_room("TEST01")
    await room.add_player("player-1", "Alice", AsyncMock())
    room.metadata.game_phase = "drawing"

    existing_response = await async_client.get("/rooms/TEST01/status")
    assert existing_response.status_code == 200
    assert existing_response.json() == {"exists": True, "players": 1, "game_phase": "drawing"}


def test_join_broadcast_lists_all_players(test_client) -> None:
    with joined_players(
        test_client,
        "JOIN01",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (ws1, ws2):
        send_json(ws1, {"type": "request_game_state", "playerId": "player-1"})
        send_json(ws2, {"type": "request_game_state", "playerId": "player-2"})

        assert receive_json(ws1)["players"] == receive_json(ws2)["players"]


def test_player_disconnect_broadcasts_player_left(test_client) -> None:
    with joined_players(
        test_client,
        "DISC01",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (ws1, ws2):
        ws1.close()

        assert receive_json(ws2) == {"type": "player_left", "playerId": "player-1"}


def test_request_game_state_returns_current_room_state(test_client) -> None:
    with test_client.websocket_connect("/party/STATE01") as websocket:
        initial_state = receive_json(websocket)
        assert initial_state["type"] == "room_state"

        join_player(websocket, "player-1", "Alice")
        send_json(websocket, {"type": "request_game_state", "playerId": "player-1"})

        room_state = receive_json(websocket)
        assert room_state["type"] == "room_state"
        assert room_state["players"] == [{"id": "player-1", "name": "Alice", "categories": []}]
        assert room_state["difficulty"] == "medium"
        assert room_state["maxRounds"] == 5
        assert room_state["padVisibility"] is True
        assert room_state["isPrivate"] is False


def test_ready_and_restart_messages_are_broadcast(test_client) -> None:
    with test_client.websocket_connect("/party/CONTROL01") as websocket:
        receive_json(websocket)
        join_player(websocket, "player-1", "Alice")

        send_json(websocket, {"type": "player_ready", "playerId": "player-1"})
        ready_status = receive_json(websocket)
        assert ready_status == {"type": "ready_status", "readyCount": 1, "totalPlayers": 1}

        send_json(websocket, {"type": "restart_game"})
        assert receive_json(websocket) == {"type": "restart_game"}


def test_non_host_cannot_restart_game(test_client) -> None:
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


def test_invalid_json_does_not_close_connection(test_client, sample_messages) -> None:
    with test_client.websocket_connect("/party/ERROR01") as websocket:
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

        assert receive_json(websocket)["type"] == "room_state"


def test_invalid_typed_payload_returns_protocol_error(test_client) -> None:
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


def test_invalid_start_game_difficulty_returns_protocol_error(test_client) -> None:
    with joined_players(
        test_client,
        "PROTO02",
        [JoinedPlayer("player-1", "Alice"), JoinedPlayer("player-2", "Bob")],
    ) as (_ws1, ws2):
        send_json(ws2, {"type": "start_game", "difficulty": "expert", "rounds": 3, "roundLength": 30})

        assert receive_json(ws2) == {
            "type": "protocol_error",
            "error": "invalid_payload",
            "message": "Invalid websocket payload.",
        }


def test_player_ready_requires_matching_connection_identity(test_client) -> None:
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
