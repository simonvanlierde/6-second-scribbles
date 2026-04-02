"""Tests for room hibernation and automatic garbage collection"""

import time

import pytest
from httpx import AsyncClient

from app.game_room import GameRoom, RoomManager


class TestRoomHibernation:
    """Test suite for room hibernation functionality"""

    @pytest.mark.asyncio
    async def test_room_marked_empty_on_last_player_leave(self):
        """Test that room is marked when last player leaves"""
        from app.game_room import room_manager

        room_id = "EMPTY_TEST"
        room = room_manager.get_or_create_room(room_id)

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Add a player
        ws = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws)
        assert room.is_empty() is False
        assert room._emptied_at is None

        # Remove the player
        await room.remove_player("player_1")
        assert room.is_empty() is True
        assert room._emptied_at is not None

    @pytest.mark.asyncio
    async def test_room_enters_hibernation_after_1_minute(self):
        """Test that room enters hibernation after being empty for 1 minute"""
        room = GameRoom("HIBERNATE_TEST")

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Add and remove player to mark as empty
        ws = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        # Initially not hibernated
        assert room.is_hibernated is False
        assert room.should_hibernate() is False

        # Simulate time passing (1 minute)
        room._emptied_at = time.time() - 65  # 65 seconds ago

        # Should now be eligible for hibernation
        assert room.should_hibernate() is True

        # Hibernate the room
        await room.hibernate()
        assert room.is_hibernated is True

    @pytest.mark.asyncio
    async def test_room_removed_after_5_minutes(self):
        """Test that room is marked for removal after 5 minutes empty"""
        room = GameRoom("REMOVAL_TEST")

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Add and remove player
        ws = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        # Initially should not be removed
        assert room.should_be_removed() is False

        # Simulate 5+ minutes passing
        room._emptied_at = time.time() - (5 * 60 + 10)  # 5 minutes 10 seconds ago

        # Should now be eligible for removal
        assert room.should_be_removed() is True

    @pytest.mark.asyncio
    async def test_room_wakes_from_hibernation_on_join(self):
        """Test that hibernated room wakes up when player joins"""
        room = GameRoom("WAKE_TEST")

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Manually set as hibernated
        room.is_hibernated = True
        room._emptied_at = time.time() - 120

        # Add player
        ws = MockWebSocket()
        player, _ = await room.add_player("player_1", "Player 1", ws)

        # Should be awake now
        assert room.is_hibernated is False
        assert room._emptied_at is None


class TestRoomManagerCleanup:
    """Test suite for RoomManager periodic cleanup"""

    @pytest.mark.asyncio
    async def test_room_manager_starts_and_stops(self):
        """Test that room manager can start and stop cleanly"""
        manager = RoomManager()

        # Start
        await manager.start()
        assert manager._is_running is True
        assert manager._cleanup_task is not None

        # Stop
        await manager.stop()
        assert manager._is_running is False

    @pytest.mark.asyncio
    async def test_periodic_cleanup_hibernates_rooms(self):
        """Test that periodic cleanup hibernates empty rooms"""
        manager = RoomManager()
        await manager.start()

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Create room and make it empty
        room = manager.get_or_create_room("CLEANUP_TEST")
        ws = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        # Simulate room being empty for >1 minute
        room._emptied_at = time.time() - 65

        # Run cleanup
        await manager._run_cleanup()

        # Room should be hibernated but not removed
        assert room.is_hibernated is True
        assert "CLEANUP_TEST" in manager.rooms

        await manager.stop()

    @pytest.mark.asyncio
    async def test_periodic_cleanup_removes_old_rooms(self):
        """Test that periodic cleanup removes rooms empty for >5 minutes"""
        manager = RoomManager()
        await manager.start()

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Create room and make it empty
        room = manager.get_or_create_room("OLD_ROOM")
        ws = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        # Simulate room being empty for >5 minutes
        room._emptied_at = time.time() - (5 * 60 + 10)

        # Run cleanup
        await manager._run_cleanup()

        # Room should be removed
        assert "OLD_ROOM" not in manager.rooms

        await manager.stop()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_active_rooms(self):
        """Test that cleanup doesn't affect rooms with players"""
        manager = RoomManager()
        await manager.start()

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Create active room with player
        room = manager.get_or_create_room("ACTIVE_ROOM")
        ws = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws)

        # Run cleanup
        await manager._run_cleanup()

        # Room should still exist and not be hibernated
        assert "ACTIVE_ROOM" in manager.rooms
        assert room.is_hibernated is False

        await manager.stop()


class TestRoomManagerStats:
    """Test suite for room manager statistics"""

    @pytest.mark.asyncio
    async def test_get_stats_with_no_rooms(self):
        """Test stats endpoint with no rooms"""
        manager = RoomManager()
        stats = manager.get_stats()

        assert stats["total_rooms"] == 0
        assert stats["active_rooms"] == 0
        assert stats["hibernated_rooms"] == 0
        assert stats["empty_rooms"] == 0
        assert stats["total_players"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_mixed_rooms(self):
        """Test stats with active, empty, and hibernated rooms"""
        manager = RoomManager()

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # Active room with players
        active_room = manager.get_or_create_room("ACTIVE")
        ws1 = MockWebSocket()
        await active_room.add_player("player_1", "Player 1", ws1)

        # Empty room (not hibernated yet)
        empty_room = manager.get_or_create_room("EMPTY")
        ws2 = MockWebSocket()
        await empty_room.add_player("player_2", "Player 2", ws2)
        await empty_room.remove_player("player_2")

        # Hibernated room
        hibernated_room = manager.get_or_create_room("HIBERNATED")
        ws3 = MockWebSocket()
        await hibernated_room.add_player("player_3", "Player 3", ws3)
        await hibernated_room.remove_player("player_3")
        hibernated_room.is_hibernated = True

        # Get stats
        stats = manager.get_stats()

        assert stats["total_rooms"] == 3
        assert stats["active_rooms"] == 1  # ACTIVE room
        assert stats["hibernated_rooms"] == 1  # HIBERNATED room
        assert stats["empty_rooms"] == 1  # EMPTY room
        assert stats["total_players"] == 1  # 1 player in ACTIVE room


class TestStatsEndpoint:
    """Test suite for /api/stats endpoint"""

    @pytest.mark.asyncio
    async def test_stats_endpoint_returns_stats(self, async_client: AsyncClient):
        """Test that /api/stats returns server statistics"""
        response = await async_client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ok"
        assert "total_rooms" in data
        assert "active_rooms" in data
        assert "hibernated_rooms" in data
        assert "empty_rooms" in data
        assert "total_players" in data

        # All values should be integers
        assert isinstance(data["total_rooms"], int)
        assert isinstance(data["active_rooms"], int)
        assert isinstance(data["total_players"], int)


class TestRoomLifecycle:
    """Test complete room lifecycle"""

    @pytest.mark.asyncio
    async def test_complete_room_lifecycle(self):
        """Test room from creation to hibernation to removal"""
        manager = RoomManager()
        await manager.start()

        class MockWebSocket:
            async def send_text(self, message):
                pass

        # 1. Create room
        room = manager.get_or_create_room("LIFECYCLE_TEST")
        assert "LIFECYCLE_TEST" in manager.rooms

        # 2. Players join
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await room.add_player("player_1", "Player 1", ws1)
        await room.add_player("player_2", "Player 2", ws2)
        assert len(room.players) == 2

        # 3. Players leave
        await room.remove_player("player_1")
        await room.remove_player("player_2")
        assert room.is_empty()
        assert room._emptied_at is not None

        # 4. Room enters hibernation after 1 minute
        room._emptied_at = time.time() - 65
        await manager._run_cleanup()
        assert room.is_hibernated is True
        assert "LIFECYCLE_TEST" in manager.rooms

        # 5. Room is removed after 5 minutes total
        room._emptied_at = time.time() - (5 * 60 + 10)
        await manager._run_cleanup()
        assert "LIFECYCLE_TEST" not in manager.rooms

        await manager.stop()
