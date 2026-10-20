"""Tests for matching a public room, as quick play does, and the privacy toggle that hides one."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from app.core.config import settings
from app.core.types import GamePhase
from app.rooms.manager import GameRoom, PlayerInfo, room_manager
from tests.constants import MEDIUM, START_GAME
from tests.helpers import JoinedPlayer, joined_players, receive_json, send_json

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _find_public_room() -> str | None:
    return room_manager.find_random_public_room(max_players=settings.max_players)


class TestFindPublicRoom:
    """Test suite for public room matching."""

    def test_no_available_rooms(self) -> None:
        """Test when no public rooms are available."""
        assert _find_public_room() is None

    def test_find_public_room(self, test_client: TestClient) -> None:
        """Test that a public room waiting for players is matched."""
        room_id = "CODE22"
        with joined_players(test_client, room_id, [JoinedPlayer("player1", "Test Player")]):
            assert _find_public_room() == room_id

    def test_private_room_not_returned(self, test_client: TestClient) -> None:
        """Test that private rooms are not matched."""
        room_id = "CODE19"

        with joined_players(test_client, room_id, [JoinedPlayer("host1", "Host")]):
            room = room_manager.get_room(room_id)
            assert room is not None
            room.metadata.is_private = True

            assert _find_public_room() is None

    def test_full_room_not_returned(self) -> None:
        """Test that full rooms are not matched."""
        room_id = "CODE05"
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

        assert _find_public_room() is None

    def test_mid_game_room_not_returned(self, test_client: TestClient) -> None:
        """Test that rooms in the middle of a game are not matched."""
        room_id = "CODE08"

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

            assert _find_public_room() is None


class TestPrivacyToggle:
    """Test suite for room privacy toggle."""

    def test_host_can_set_privacy(self, test_client: TestClient) -> None:
        """Test that the host can toggle room privacy and it hides the room from matching."""
        room_id = "CODE17"

        with joined_players(test_client, room_id, [JoinedPlayer("host1", "Host")]) as (ws,):
            assert _find_public_room() == room_id

            send_json(ws, {"type": "privacy_changed", "isPrivate": True})
            # The server sends nothing back, so a state request orders the check after the change.
            send_json(ws, {"type": "request_game_state", "playerId": "host1"})
            receive_json(ws)

            assert _find_public_room() is None

    def test_non_host_cannot_set_privacy(self, test_client: TestClient) -> None:
        """Test that a non-host player cannot toggle room privacy."""
        room_id = "CODE16"

        with joined_players(
            test_client,
            room_id,
            [JoinedPlayer("host1", "Host"), JoinedPlayer("player2", "Player 2")],
        ) as (_, ws2):
            send_json(ws2, {"type": "privacy_changed", "isPrivate": True})

            room = room_manager.get_room(room_id)
            assert room is not None
            assert not room.metadata.is_private
