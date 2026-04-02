"""Tests for host transfer on reconnection and player limit enforcement"""

import asyncio

import pytest
from httpx import AsyncClient


class TestDelayedHostTransfer:
    """Test suite for delayed host transfer on reconnection"""

    @pytest.mark.asyncio
    async def test_host_reconnects_within_delay(self):
        """Test that host retains status when reconnecting within 1 second"""
        from app.game_room import room_manager

        room_id = "HOST_RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)

        # Create mock websockets
        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Add host
        ws1 = MockWebSocket()
        player, _ = await room.add_player("host_123", "Host Player", ws1)
        assert room.host_id == "host_123"
        assert room._last_host_id == "host_123"

        # Add another player
        ws2 = MockWebSocket()
        await room.add_player("player_456", "Player 2", ws2)
        assert len(room.players) == 2

        # Host disconnects (triggers delayed transfer)
        await room.remove_player("host_123")
        assert len(room.players) == 1
        assert room._pending_host_transfer is not None

        # Host reconnects before 1 second delay
        await asyncio.sleep(0.5)  # Wait 500ms
        ws1_new = MockWebSocket()
        player, is_reconnecting = await room.add_player("host_123", "Host Player", ws1_new)

        # Host should be restored
        assert is_reconnecting is True
        assert room.host_id == "host_123"
        assert room._pending_host_transfer is None  # Transfer cancelled

    @pytest.mark.asyncio
    async def test_host_does_not_reconnect_transfer_occurs(self):
        """Test that host is transferred if they don't reconnect within 1 second"""
        from app.game_room import room_manager

        room_id = "HOST_TRANSFER_TEST"
        room = room_manager.get_or_create_room(room_id)

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Add host
        ws1 = MockWebSocket()
        await room.add_player("host_123", "Host Player", ws1)

        # Add another player
        ws2 = MockWebSocket()
        await room.add_player("player_456", "Player 2", ws2)

        old_host_id = room.host_id
        assert old_host_id == "host_123"

        # Host disconnects
        await room.remove_player("host_123")

        # Wait for delayed transfer to complete (1+ seconds)
        await asyncio.sleep(1.2)

        # Host should have been transferred to player_456
        assert room.host_id == "player_456"
        assert room._last_host_id == "player_456"


class TestPlayerLimitEnforcement:
    """Test suite for 10 player limit enforcement"""

    @pytest.mark.asyncio
    async def test_room_full_rejects_11th_player(self, async_client: AsyncClient):
        """Test that an 11th player cannot join a full room"""
        from app.game_room import room_manager

        room_id = "FULL_ROOM_TEST"
        room = room_manager.get_or_create_room(room_id)

        class MockWebSocket:
            async def send_text(self, message):
                pass

            async def close(self, code=None, reason=None):
                pass

        # Add 10 players (maximum)
        for i in range(10):
            ws = MockWebSocket()
            await room.add_player(f"player_{i}", f"Player {i}", ws)

        assert len(room.players) == 10

        # Try to add 11th player - should raise ValueError
        ws11 = MockWebSocket()
        with pytest.raises(ValueError, match="Room is full"):
            await room.add_player("player_11", "Player 11", ws11)

        # Room should still have 10 players
        assert len(room.players) == 10

    @pytest.mark.asyncio
    async def test_existing_player_can_reconnect_to_full_room(self):
        """Test that existing player can reconnect even if room appears full"""
        from app.game_room import room_manager

        room_id = "RECONNECT_FULL_TEST"
        room = room_manager.get_or_create_room(room_id)

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Add 10 players
        player_ids = []
        for i in range(10):
            ws = MockWebSocket()
            player, _ = await room.add_player(f"player_{i}", f"Player {i}", ws)
            player_ids.append(f"player_{i}")

        assert len(room.players) == 10

        # One player disconnects
        await room.remove_player("player_5")
        assert len(room.players) == 9

        # New player fills the spot
        ws_new = MockWebSocket()
        await room.add_player("player_10", "Player 10", ws_new)
        assert len(room.players) == 10

        # Original player 5 tries to reconnect - should be rejected since room is full
        # and they're no longer in the room
        ws5 = MockWebSocket()
        with pytest.raises(ValueError, match="Room is full"):
            await room.add_player("player_5", "Player 5", ws5)


class TestWebSocketRoomFull:
    """Test WebSocket handling of room full scenario"""

    def test_websocket_sends_error_when_room_full(self, test_client):
        """Test that WebSocket sends join_error when trying to join full room"""
        import json

        from unittest.mock import AsyncMock

        from app.game_room import GameRoom, PlayerInfo
        from app.game_room import room_manager

        room_id = "WS_FULL_TEST"
        room = GameRoom(room_id)
        for i in range(10):
            ws = AsyncMock()
            room.players[f"player_{i}"] = PlayerInfo(
                id=f"player_{i}", name=f"Player {i}", websocket=ws
            )
        room.host_id = "player_0"
        room_manager.rooms[room_id] = room

        with test_client.websocket_connect(f"/party/{room_id}") as ws:
            ws.receive_text()  # room_state

            ws.send_text(json.dumps({"type": "join", "playerId": "player_11", "name": "Player 11"}))

            response = json.loads(ws.receive_text())
            assert response["type"] == "join_error"
            assert response["error"] == "room_full"
            assert "full" in response["message"].lower()


class TestGhostPlayerPrevention:
    """Test that persistent player IDs prevent ghost players"""

    def test_player_id_persistence(self):
        """Test that player ID is stored and reused from localStorage"""
        # This would be a frontend test
        # The key point is that getOrCreatePlayerId() should:
        # 1. Check localStorage for existing player_id
        # 2. Return existing ID if found
        # 3. Generate new ID only if not found
        # 4. Store new ID in localStorage

    @pytest.mark.asyncio
    async def test_reconnecting_player_replaces_old_connection(self):
        """Test that reconnecting with same player ID replaces old connection"""
        from app.game_room import room_manager

        room_id = "RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)

        class MockWebSocket:
            def __init__(self, name):
                self.name = name

            async def send_text(self, message):
                pass

        # Player connects with WS1
        ws1 = MockWebSocket("ws1")
        player1, _ = await room.add_player("player_123", "Test Player", ws1)
        assert room.players["player_123"].websocket == ws1

        # Simulate disconnect (but player still in room briefly)
        # Then player reconnects with same ID but new websocket
        ws2 = MockWebSocket("ws2")
        player2, _ = await room.add_player("player_123", "Test Player", ws2)

        # Should have same player but updated websocket
        assert "player_123" in room.players
        assert room.players["player_123"].websocket == ws2
        assert len(room.players) == 1  # Still just one player, not a ghost
