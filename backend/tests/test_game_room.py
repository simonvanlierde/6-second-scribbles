"""Tests for game room management functionality."""

import json
import time
from unittest.mock import patch

from app.game_room import GameRoom


class TestGameRoom:
    """Test suite for GameRoom class."""

    async def test_create_room(self, room_id) -> None:
        """Test creating a new game room."""
        room = GameRoom(room_id)
        assert room.room_id == room_id
        assert len(room.players) == 0
        assert room.host_id is None
        assert room.metadata.game_phase == "lobby"

    async def test_add_first_player_becomes_host(self, game_room, mock_websocket) -> None:
        """Test that the first player to join becomes the host."""
        player_id = "player-1"
        player_name = "Alice"

        await game_room.add_player(player_id, player_name, mock_websocket)

        assert len(game_room.players) == 1
        assert game_room.host_id == player_id
        assert game_room.players[player_id].name == player_name

    async def test_add_multiple_players(self, game_room, make_ws) -> None:
        """Test adding multiple players to a room."""
        ws1, ws2, ws3 = make_ws(), make_ws(), make_ws()

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)
        await game_room.add_player("player-3", "Charlie", ws3)

        assert len(game_room.players) == 3
        assert game_room.host_id == "player-1"  # First player is host

    async def test_remove_player(self, game_room, mock_websocket) -> None:
        """Test removing a player from the room."""
        await game_room.add_player("player-1", "Alice", mock_websocket)
        assert len(game_room.players) == 1

        await game_room.remove_player("player-1")
        assert len(game_room.players) == 0

    async def test_host_transfer_on_host_leave(self, game_room, make_ws, monkeypatch) -> None:
        """Test that host is transferred when the host leaves."""
        ws1, ws2 = make_ws(), make_ws()
        monkeypatch.setattr("app.game_room.settings.host_transfer_delay_ms", 0)

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)

        assert game_room.host_id == "player-1"

        await game_room.remove_player("player-1")
        assert game_room._pending_host_transfer is not None
        await game_room._pending_host_transfer

        assert game_room.host_id == "player-2"

        # Verify the host_changed message content was broadcast to Bob
        messages = [json.loads(message) for message in ws2.sent_texts]
        host_changed = next((m for m in messages if m.get("type") == "host_changed"), None)
        assert host_changed is not None
        assert host_changed["newHostId"] == "player-2"

    async def test_no_host_when_room_empty(self, game_room, mock_websocket) -> None:
        """Test that host_id is None when all players leave."""
        await game_room.add_player("player-1", "Alice", mock_websocket)
        await game_room.remove_player("player-1")

        assert game_room.host_id is None
        assert len(game_room.players) == 0

    async def test_update_player_activity(self, game_room, mock_websocket) -> None:
        """Test updating player's last activity timestamp."""
        with patch("app.game_room.time.time", side_effect=[1000.0, 1000.0, 1001.0]):
            await game_room.add_player("player-1", "Alice", mock_websocket)
            initial_time = game_room.players["player-1"].last_activity

            game_room.update_player_activity("player-1")
            updated_time = game_room.players["player-1"].last_activity

        assert updated_time > initial_time

    async def test_broadcast_to_all_players(self, room_with_players) -> None:
        """Test broadcasting a message to all players."""
        message = {"type": "test", "data": "hello"}

        await room_with_players.broadcast(message)

        for player in room_with_players.players.values():
            assert player.websocket.sent_texts == [json.dumps(message)]

    async def test_broadcast_exclude_player(self, room_with_players) -> None:
        """Test broadcasting with exclusion."""
        message = {"type": "test", "data": "hello"}

        await room_with_players.broadcast(message, exclude="player-1")

        player1 = room_with_players.players["player-1"]
        player2 = room_with_players.players["player-2"]

        assert player1.websocket.sent_texts == []
        assert player2.websocket.sent_texts == [json.dumps(message)]

    async def test_send_to_specific_player(self, room_with_players) -> None:
        """Test sending a message to a specific player."""
        message = {"type": "test", "data": "hello"}

        await room_with_players.send_to_player("player-1", message)

        player1 = room_with_players.players["player-1"]
        player2 = room_with_players.players["player-2"]

        assert player1.websocket.sent_texts == [json.dumps(message)]
        assert player2.websocket.sent_texts == []

    async def test_get_player_list(self, room_with_players) -> None:
        """Test getting the list of players."""
        player_list = room_with_players.get_player_list()

        assert len(player_list) == 2
        assert {"id": "player-1", "name": "Alice"} in player_list
        assert {"id": "player-2", "name": "Bob"} in player_list

    async def test_is_empty(self, game_room, mock_websocket) -> None:
        """Test checking if room is empty."""
        assert game_room.is_empty() is True

        await game_room.add_player("player-1", "Alice", mock_websocket)
        assert game_room.is_empty() is False

        await game_room.remove_player("player-1")
        assert game_room.is_empty() is True

    async def test_metadata_initialization(self, game_room) -> None:
        """Test that room metadata is properly initialized."""
        assert game_room.metadata.game_phase == "lobby"
        assert game_room.metadata.difficulty == "medium"
        assert game_room.metadata.max_rounds == 5
        assert game_room.metadata.pad_visibility is True
        assert len(game_room.metadata.ready_players) == 0

    async def test_ready_players_tracking(self, room_with_players) -> None:
        """Test tracking ready players."""
        assert len(room_with_players.metadata.ready_players) == 0

        room_with_players.metadata.ready_players.add("player-1")
        assert len(room_with_players.metadata.ready_players) == 1

        room_with_players.metadata.ready_players.add("player-2")
        assert len(room_with_players.metadata.ready_players) == 2

    async def test_broadcast_handles_disconnected_player(self, game_room, make_ws) -> None:
        """Test that broadcast handles disconnected players gracefully."""
        ws1 = make_ws()
        ws2 = make_ws(send_error=Exception("Connection closed"))

        await game_room.add_player("player-1", "Alice", ws1)
        await game_room.add_player("player-2", "Bob", ws2)

        message = {"type": "test"}
        await game_room.broadcast(message)

        # Player 2 should be removed due to error
        assert "player-2" not in game_room.players
        assert "player-1" in game_room.players

    async def test_room_marked_empty_after_all_disconnect(self, game_room, mock_websocket) -> None:
        """Test that room is marked as empty after all players disconnect.

        Note: rooms are not immediately removed — the periodic cleanup loop
        handles hibernation (1 min) and removal (5 min).
        """
        await game_room.add_player("player-1", "Alice", mock_websocket)
        assert not game_room.is_empty()

        await game_room.remove_player("player-1")

        assert game_room.is_empty()
        assert game_room._emptied_at is not None


class TestRoomManager:
    """Test suite for RoomManager class."""

    def test_create_room_manager(self, room_manager) -> None:
        """Test creating a room manager."""
        assert len(room_manager.rooms) == 0

    async def test_get_or_create_room(self, room_manager) -> None:
        """Test getting or creating a room."""
        room_id = "TEST01"

        # First call should create a new room
        room1 = room_manager.get_or_create_room(room_id)
        assert room1.room_id == room_id
        assert len(room_manager.rooms) == 1

        # Second call should return the same room
        room2 = room_manager.get_or_create_room(room_id)
        assert room1 is room2
        assert len(room_manager.rooms) == 1

    async def test_get_room(self, room_manager) -> None:
        """Test getting an existing room."""
        room_id = "TEST01"

        # Room doesn't exist yet
        assert room_manager.get_room(room_id) is None

        # Create room
        room_manager.get_or_create_room(room_id)

        # Now it should exist
        room = room_manager.get_room(room_id)
        assert room is not None
        assert room.room_id == room_id

    async def test_remove_room(self, room_manager) -> None:
        """Test removing a room."""
        room_id = "TEST01"
        room_manager.get_or_create_room(room_id)

        assert len(room_manager.rooms) == 1

        await room_manager.remove_room(room_id)
        assert len(room_manager.rooms) == 0

    async def test_cleanup_empty_rooms(self, room_manager, make_ws) -> None:
        """Test cleaning up empty rooms."""
        # Create multiple rooms
        room1 = room_manager.get_or_create_room("ROOM01")
        room_manager.get_or_create_room("ROOM02")
        room3 = room_manager.get_or_create_room("ROOM03")

        # Add players to some rooms
        ws1, ws2 = make_ws(), make_ws()
        await room1.add_player("p1", "Alice", ws1)
        await room3.add_player("p2", "Bob", ws2)

        # room2 is empty, should be cleaned up
        await room_manager.cleanup_empty_rooms()

        assert "ROOM01" in room_manager.rooms
        assert "ROOM02" not in room_manager.rooms
        assert "ROOM03" in room_manager.rooms


class TestIdlePlayerDetection:
    """Test suite for idle player detection."""

    async def test_idle_check_only_during_active_game(self, game_room, mock_websocket) -> None:
        """Test that idle check only runs during active game phases."""
        await game_room.add_player("player-1", "Alice", mock_websocket)

        # In lobby phase, no idle checks
        game_room.metadata.game_phase = "lobby"
        await game_room._check_idle_players()
        assert "player-1" in game_room.players

        # In complete phase, no idle checks
        game_room.metadata.game_phase = "complete"
        await game_room._check_idle_players()
        assert "player-1" in game_room.players

    async def test_idle_player_detection(self, game_room, mock_websocket) -> None:
        """Test detecting and disconnecting idle players."""
        await game_room.add_player("player-1", "Alice", mock_websocket)

        # Set game to active phase
        game_room.metadata.game_phase = "drawing"

        # Simulate old activity (more than 3 minutes ago)
        old_time = time.time() - (4 * 60)  # 4 minutes ago
        game_room.players["player-1"].last_activity = old_time

        # Check for idle players
        await game_room._check_idle_players()

        # Player should be disconnected
        assert mock_websocket.close_calls == [{"code": 1000, "reason": "Disconnected due to inactivity"}]

    async def test_active_player_not_disconnected(self, game_room, mock_websocket) -> None:
        """Test that active players are not disconnected."""
        await game_room.add_player("player-1", "Alice", mock_websocket)

        game_room.metadata.game_phase = "drawing"

        # Update activity to now
        game_room.update_player_activity("player-1")

        # Check for idle players
        await game_room._check_idle_players()

        # Player should still be connected
        assert "player-1" in game_room.players
        assert mock_websocket.close_calls == []
