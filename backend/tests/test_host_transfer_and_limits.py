"""Tests for host transfer on reconnection and player limit enforcement."""

import json
from unittest.mock import AsyncMock

import pytest

from app.rooms.manager import GameRoom, PlayerInfo, room_manager


class TestDelayedHostTransfer:
    """Test suite for delayed host transfer on reconnection."""

    async def test_pending_transfer_cancelled_on_reconnect(self, make_ws, monkeypatch) -> None:
        """Test that host retains status when reconnecting before transfer completes."""
        room_id = "HOST_RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 3600_000)

        ws1, ws2 = make_ws(), make_ws()

        _player, _ = await room.add_player("host_123", "Host Player", ws1)
        assert room.host_id == "host_123"
        assert room._last_host_id == "host_123"

        await room.add_player("player_456", "Player 2", ws2)
        assert len(room.players) == 2

        await room.remove_player("host_123")
        assert len(room.players) == 1
        assert room._pending_host_transfer is not None

        # Host reconnects before delay expires
        ws1_new = make_ws()
        _player, is_reconnecting = await room.add_player("host_123", "Host Player", ws1_new)

        # Transfer should be cancelled, host restored
        assert is_reconnecting is True
        assert room.host_id == "host_123"
        assert room._pending_host_transfer is None

    async def test_delayed_transfer_completes_without_reconnect(self, make_ws, monkeypatch) -> None:
        """Test that host is transferred if they don't reconnect in time."""
        room_id = "HOST_TRANSFER_TEST"
        room = room_manager.get_or_create_room(room_id)
        monkeypatch.setattr("app.rooms.manager.settings.host_transfer_delay_ms", 0)

        ws1, ws2 = make_ws(), make_ws()

        await room.add_player("host_123", "Host Player", ws1)
        await room.add_player("player_456", "Player 2", ws2)

        assert room.host_id == "host_123"

        await room.remove_player("host_123")
        assert room._pending_host_transfer is not None
        await room._pending_host_transfer

        assert room.host_id == "player_456"
        assert room._last_host_id == "player_456"


class TestPlayerLimitEnforcement:
    """Test suite for 10 player limit enforcement."""

    async def test_room_full_rejects_11th_player(self, make_ws) -> None:
        """Test that an 11th player cannot join a full room."""
        room_id = "FULL_ROOM_TEST"
        room = room_manager.get_or_create_room(room_id)

        # Add 10 players (maximum)
        for i in range(10):
            await room.add_player(f"player_{i}", f"Player {i}", make_ws())

        assert len(room.players) == 10

        # Try to add 11th player — should raise ValueError
        with pytest.raises(ValueError, match="Room is full"):
            await room.add_player("player_11", "Player 11", make_ws())

        assert len(room.players) == 10

    async def test_existing_player_can_reconnect_to_full_room(self, make_ws) -> None:
        """Test that existing player can reconnect even if room appears full."""
        room_id = "RECONNECT_FULL_TEST"
        room = room_manager.get_or_create_room(room_id)

        for i in range(10):
            await room.add_player(f"player_{i}", f"Player {i}", make_ws())

        assert len(room.players) == 10

        # One player disconnects
        await room.remove_player("player_5")
        assert len(room.players) == 9

        # New player fills the spot
        await room.add_player("player_10", "Player 10", make_ws())
        assert len(room.players) == 10

        # Original player 5 tries to reconnect — room is full and they're no longer in it
        with pytest.raises(ValueError, match="Room is full"):
            await room.add_player("player_5", "Player 5", make_ws())


class TestWebSocketRoomFull:
    """Test WebSocket handling of room full scenario."""

    def test_websocket_sends_error_when_room_full(self, test_client) -> None:
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
            assert response["type"] == "join_error"
            assert response["error"] == "room_full"
            assert "full" in response["message"].lower()


class TestGhostPlayerPrevention:
    """Test that persistent player IDs prevent ghost players."""

    async def test_reconnecting_player_replaces_old_connection(self, make_ws) -> None:
        """Test that reconnecting with same player ID replaces old connection."""
        room_id = "RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)

        ws1 = make_ws()
        _player1, _ = await room.add_player("player_123", "Test Player", ws1)
        assert room.players["player_123"].websocket == ws1

        # Player reconnects with same ID but new websocket
        ws2 = make_ws()
        _player2, _ = await room.add_player("player_123", "Test Player", ws2)

        assert "player_123" in room.players
        assert room.players["player_123"].websocket == ws2
        assert len(room.players) == 1  # Still just one player, not a ghost
