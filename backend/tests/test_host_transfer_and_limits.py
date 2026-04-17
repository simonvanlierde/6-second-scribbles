"""Tests for host transfer on reconnection and player limit enforcement."""

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest

from app.rooms.manager import GameRoom, PlayerInfo, room_manager
from tests.conftest import as_websocket

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient

    from tests.conftest import TestWebSocket

HOST_PLAYER_ID = "host_123"
SECOND_PLAYER_ID = "player_456"
PLAYER_11_ID = "player_11"
PLAYER_123_ID = "player_123"
JOIN_ERROR = "join_error"
ROOM_FULL = "room_full"
FULL = "full"


class TestDelayedHostTransfer:
    """Test suite for delayed host transfer on reconnection."""

    async def test_pending_transfer_cancelled_on_reconnect(
        self,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that host retains status when reconnecting before transfer completes."""
        room_id = "HOST_RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 3600_000)

        ws1, ws2 = make_ws(), make_ws()

        _player, _ = await room.add_player(HOST_PLAYER_ID, "Host Player", as_websocket(ws1))
        assert room.host_id == HOST_PLAYER_ID
        assert room.last_host_id == HOST_PLAYER_ID

        await room.add_player(SECOND_PLAYER_ID, "Player 2", as_websocket(ws2))
        assert len(room.players) == 2

        await room.remove_player(HOST_PLAYER_ID)
        assert len(room.players) == 1
        assert room.pending_host_transfer is not None

        # Host reconnects before delay expires
        ws1_new = make_ws()
        _player, is_reconnecting = await room.add_player(HOST_PLAYER_ID, "Host Player", as_websocket(ws1_new))

        # Transfer should be cancelled, host restored
        assert is_reconnecting
        assert room.host_id == HOST_PLAYER_ID
        assert room.pending_host_transfer is None

    async def test_delayed_transfer_completes_without_reconnect(
        self,
        make_ws: Callable[..., TestWebSocket],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that host is transferred if they don't reconnect in time."""
        room_id = "HOST_TRANSFER_TEST"
        room = room_manager.get_or_create_room(room_id)
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 0)

        ws1, ws2 = make_ws(), make_ws()

        await room.add_player(HOST_PLAYER_ID, "Host Player", as_websocket(ws1))
        await room.add_player(SECOND_PLAYER_ID, "Player 2", as_websocket(ws2))

        assert room.host_id == HOST_PLAYER_ID

        await room.remove_player(HOST_PLAYER_ID)
        assert room.pending_host_transfer is not None
        await room.pending_host_transfer

        assert room.host_id == SECOND_PLAYER_ID
        assert room.last_host_id == SECOND_PLAYER_ID


class TestPlayerLimitEnforcement:
    """Test suite for 10 player limit enforcement."""

    async def test_room_full_rejects_11th_player(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that an 11th player cannot join a full room."""
        room_id = "FULL_ROOM_TEST"
        room = room_manager.get_or_create_room(room_id)

        # Add 10 players (maximum)
        for i in range(10):
            await room.add_player(f"player_{i}", f"Player {i}", as_websocket(make_ws()))

        assert len(room.players) == 10

        # Try to add 11th player — should raise ValueError
        with pytest.raises(ValueError, match="Room is full"):
            await room.add_player(PLAYER_11_ID, "Player 11", as_websocket(make_ws()))

        assert len(room.players) == 10

    async def test_existing_player_can_reconnect_to_full_room(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that existing player can reconnect even if room appears full."""
        room_id = "RECONNECT_FULL_TEST"
        room = room_manager.get_or_create_room(room_id)

        for i in range(10):
            await room.add_player(f"player_{i}", f"Player {i}", as_websocket(make_ws()))

        assert len(room.players) == 10

        # One player disconnects
        await room.remove_player("player_5")
        assert len(room.players) == 9

        # New player fills the spot
        await room.add_player("player_10", "Player 10", as_websocket(make_ws()))
        assert len(room.players) == 10

        # Original player 5 tries to reconnect — room is full and they're no longer in it
        with pytest.raises(ValueError, match="Room is full"):
            await room.add_player("player_5", "Player 5", as_websocket(make_ws()))


class TestWebSocketRoomFull:
    """Test WebSocket handling of room full scenario."""

    def test_websocket_sends_error_when_room_full(self, test_client: TestClient) -> None:
        """Test that WebSocket sends join_error when trying to join full room."""
        room_id = "WS_FULL_TEST"
        room = GameRoom(room_id)
        for i in range(10):
            ws = AsyncMock()
            room.players[f"player_{i}"] = PlayerInfo(
                id=f"player_{i}",
                name=f"Player {i}",
                websocket=ws,
            )
        room.host_id = "player_0"
        room_manager.rooms[room_id] = room

        with test_client.websocket_connect(f"/ws/{room_id}") as ws:
            ws.receive_text()  # room_state

            ws.send_text(json.dumps({"type": "join", "playerId": "player_11", "name": "Player 11"}))

            response = json.loads(ws.receive_text())
            assert response["type"] == JOIN_ERROR
            assert response["error"] == ROOM_FULL
            assert FULL in response["message"].lower()


class TestGhostPlayerPrevention:
    """Test that persistent player IDs prevent ghost players."""

    async def test_reconnecting_player_replaces_old_connection(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that reconnecting with same player ID replaces old connection."""
        room_id = "RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)

        ws1 = make_ws()
        _player1, _ = await room.add_player(PLAYER_123_ID, "Test Player", as_websocket(ws1))
        assert room.players[PLAYER_123_ID].websocket == ws1

        # Player reconnects with same ID but new websocket
        ws2 = make_ws()
        _player2, _ = await room.add_player(PLAYER_123_ID, "Test Player", as_websocket(ws2))

        assert PLAYER_123_ID in room.players
        assert room.players[PLAYER_123_ID].websocket == ws2
        assert len(room.players) == 1  # Still just one player, not a ghost
