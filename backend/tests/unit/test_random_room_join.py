"""Tests for random room join functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from app.core.types import GamePhase
from app.rooms.manager import GameRoom, PlayerInfo, room_manager
from tests.constants import MEDIUM, START_GAME
from tests.helpers import JoinedPlayer, joined_players, receive_json, send_json

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

DETAIL = "detail"
NO_AVAILABLE = "no available"


class TestRandomRoomJoin:
    """Test suite for random room join feature."""

    def test_no_available_rooms(self, test_client: TestClient) -> None:
        """Test when no public rooms are available."""
        response = test_client.get("/api/rooms/random")

        assert response.status_code == 404
        data = response.json()
        assert DETAIL in data
        assert NO_AVAILABLE in data[DETAIL].lower()

    def test_find_public_room(self, test_client: TestClient) -> None:
        """Test that a public room waiting for players is returned by random join."""
        room_id = "PUBLIC_ROOM_01"
        with joined_players(test_client, room_id, [JoinedPlayer("player1", "Test Player")]):
            response = test_client.get("/api/rooms/random")

            assert response.status_code == 200
            data = response.json()
            assert data["room_code"] == room_id
            assert data["player_count"] == 1
            assert data["max_players"] == 10

    def test_private_room_not_returned(self, test_client: TestClient) -> None:
        """Test that private rooms are excluded by random join."""
        room_id = "PRIVATE_ROOM"

        with joined_players(test_client, room_id, [JoinedPlayer("host1", "Host")]):
            room = room_manager.get_room(room_id)
            assert room is not None
            room.metadata.is_private = True

            response = test_client.get("/api/rooms/random")
            assert response.status_code == 404

    def test_full_room_not_returned(self, test_client: TestClient) -> None:
        """Test that full rooms are not returned by random join."""
        room_id = "FULL_ROOM"
        room = GameRoom(room_id)
        for i in range(10):
            ws = AsyncMock()
            room.players[f"player-{i}"] = PlayerInfo(
                id=f"player-{i}",
                name=f"Player {i}",
                websocket=ws,
            )
        room.host_id = "player-0"
        room_manager.rooms[room_id] = room

        response = test_client.get("/api/rooms/random")
        assert response.status_code == 404

    def test_mid_game_room_not_returned(self, test_client: TestClient) -> None:
        """Test that rooms in the middle of a game are not returned by random join."""
        room_id = "GAMING_ROOM"

        with joined_players(
            test_client,
            room_id,
            [JoinedPlayer("player1", "Player 1"), JoinedPlayer("player2", "Player 2")],
        ) as (ws1, ws2):
            send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 3, "drawingTimeLimit": 60})
            assert [receive_json(ws1)["type"], receive_json(ws2)["type"]] == [START_GAME, START_GAME]

            room = room_manager.get_room(room_id)
            assert room is not None
            room.metadata.game_phase = GamePhase.DRAWING

            response = test_client.get("/api/rooms/random")
            assert response.status_code == 404


class TestPrivacyToggle:
    """Test suite for room privacy toggle."""

    def test_host_can_set_privacy(self, test_client: TestClient) -> None:
        """Test that the host can toggle room privacy and it affects random join."""
        room_id = "PRIVACY_TEST"

        with joined_players(test_client, room_id, [JoinedPlayer("host1", "Host")]) as (ws,):
            response = test_client.get("/api/rooms/random")
            assert response.status_code == 200
            assert response.json()["room_code"] == room_id

            send_json(ws, {"type": "privacy_changed", "isPrivate": True})

            response = test_client.get("/api/rooms/random")
            assert response.status_code == 404

    def test_non_host_cannot_set_privacy(self, test_client: TestClient) -> None:
        """Test that a non-host player cannot toggle room privacy."""
        room_id = "NON_HOST_PRIVACY"

        with joined_players(
            test_client,
            room_id,
            [JoinedPlayer("host1", "Host"), JoinedPlayer("player2", "Player 2")],
        ) as (_, ws2):
            send_json(ws2, {"type": "privacy_changed", "isPrivate": True})

            room = room_manager.get_room(room_id)
            assert room is not None
            assert not room.metadata.is_private
