"""Tests for room hibernation and automatic garbage collection."""

import time
from typing import TYPE_CHECKING

import pytest

from app.game_room import GameRoom, RoomManager, room_manager

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestRoomHibernation:
    """Test suite for room hibernation functionality."""

    async def test_room_marked_empty_on_last_player_leave(self, make_ws) -> None:
        """Test that room is marked when last player leaves."""
        room_id = "EMPTY_TEST"
        room = room_manager.get_or_create_room(room_id)

        ws = make_ws()
        await room.add_player("player_1", "Player 1", ws)
        assert room.is_empty() is False
        assert room._emptied_at is None

        await room.remove_player("player_1")
        assert room.is_empty() is True
        assert room._emptied_at is not None

    async def test_room_enters_hibernation_after_1_minute(self, make_ws) -> None:
        """Test that room enters hibernation after being empty for 1 minute."""
        room = GameRoom("HIBERNATE_TEST")

        ws = make_ws()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        assert room.is_hibernated is False
        assert room.should_hibernate() is False

        # Simulate time passing (1 minute) — direct state manipulation is the correct approach
        room._emptied_at = time.time() - 65

        assert room.should_hibernate() is True

        await room.hibernate()
        assert room.is_hibernated is True

    async def test_room_removed_after_5_minutes(self, make_ws) -> None:
        """Test that room is marked for removal after 5 minutes empty."""
        room = GameRoom("REMOVAL_TEST")

        ws = make_ws()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        assert room.should_be_removed() is False

        room._emptied_at = time.time() - (5 * 60 + 10)

        assert room.should_be_removed() is True

    async def test_room_wakes_from_hibernation_on_join(self, make_ws) -> None:
        """Test that hibernated room wakes up when player joins."""
        room = GameRoom("WAKE_TEST")

        room.is_hibernated = True
        room._emptied_at = time.time() - 120

        ws = make_ws()
        _player, _ = await room.add_player("player_1", "Player 1", ws)

        assert room.is_hibernated is False
        assert room._emptied_at is None


class TestRoomManagerCleanup:
    """Test suite for RoomManager periodic cleanup."""

    async def test_room_manager_starts_and_stops(self) -> None:
        """Test that room manager can start and stop cleanly."""
        manager = RoomManager()

        await manager.start()
        assert manager._is_running is True
        assert manager._cleanup_task is not None

        await manager.stop()
        assert manager._is_running is False

    @pytest.mark.parametrize(
        ("empty_seconds", "expect_hibernated", "expect_removed"),
        [
            (65, True, False),  # 1 min → hibernate only
            (5 * 60 + 10, True, True),  # 5 min → remove
        ],
    )
    async def test_cleanup_state_transitions(
        self,
        managed_room_manager,
        make_ws,
        empty_seconds,
        expect_hibernated,
        expect_removed,
    ) -> None:
        """Test periodic cleanup transitions: hibernate after 1 min, remove after 5 min."""
        room = managed_room_manager.get_or_create_room("CLEANUP_STATE_TEST")
        ws = make_ws()
        await room.add_player("player_1", "Player 1", ws)
        await room.remove_player("player_1")

        room._emptied_at = time.time() - empty_seconds

        await managed_room_manager._run_cleanup()

        if expect_removed:
            assert "CLEANUP_STATE_TEST" not in managed_room_manager.rooms
        else:
            assert "CLEANUP_STATE_TEST" in managed_room_manager.rooms
            assert room.is_hibernated is expect_hibernated

    async def test_cleanup_keeps_active_rooms(self, managed_room_manager, make_ws) -> None:
        """Test that cleanup doesn't affect rooms with players."""
        room = managed_room_manager.get_or_create_room("ACTIVE_ROOM")
        ws = make_ws()
        await room.add_player("player_1", "Player 1", ws)

        await managed_room_manager._run_cleanup()

        assert "ACTIVE_ROOM" in managed_room_manager.rooms
        assert room.is_hibernated is False


class TestRoomManagerStats:
    """Test suite for room manager statistics."""

    async def test_get_stats_with_mixed_rooms(self, make_ws) -> None:
        """Test stats with active, empty, and hibernated rooms."""
        manager = RoomManager()

        # Active room with players
        active_room = manager.get_or_create_room("ACTIVE")
        ws1 = make_ws()
        await active_room.add_player("player_1", "Player 1", ws1)

        # Empty room (not hibernated yet)
        empty_room = manager.get_or_create_room("EMPTY")
        ws2 = make_ws()
        await empty_room.add_player("player_2", "Player 2", ws2)
        await empty_room.remove_player("player_2")

        # Hibernated room
        hibernated_room = manager.get_or_create_room("HIBERNATED")
        ws3 = make_ws()
        await hibernated_room.add_player("player_3", "Player 3", ws3)
        await hibernated_room.remove_player("player_3")
        hibernated_room.is_hibernated = True

        stats = manager.get_stats()

        assert stats["total_rooms"] == 3
        assert stats["active_rooms"] == 1
        assert stats["hibernated_rooms"] == 1
        assert stats["empty_rooms"] == 1
        assert stats["total_players"] == 1


class TestStatsEndpoint:
    """Test suite for /api/stats endpoint."""

    async def test_stats_endpoint_returns_stats(self, async_client: AsyncClient) -> None:
        """Test that /api/stats returns server statistics with correct structure."""
        # Baseline: no rooms
        response = await async_client.get("/api/stats")
        assert response.status_code == 200
        data_before = response.json()

        assert data_before["status"] == "ok"
        for key in ("total_rooms", "active_rooms", "hibernated_rooms", "empty_rooms", "total_players"):
            assert key in data_before
            assert isinstance(data_before[key], int)

        # Create a room and verify total_rooms increases
        room_manager.get_or_create_room("STATS_TEST_ROOM")
        response = await async_client.get("/api/stats")
        assert response.status_code == 200
        data_after = response.json()
        assert data_after["total_rooms"] == data_before["total_rooms"] + 1


class TestRoomLifecycle:
    """Test complete room lifecycle."""

    async def test_complete_room_lifecycle(self, managed_room_manager, make_ws) -> None:
        """Test room from creation to hibernation to removal."""
        # 1. Create room
        room = managed_room_manager.get_or_create_room("LIFECYCLE_TEST")
        assert "LIFECYCLE_TEST" in managed_room_manager.rooms

        # 2. Players join
        ws1, ws2 = make_ws(), make_ws()
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
        await managed_room_manager._run_cleanup()
        assert room.is_hibernated is True
        assert "LIFECYCLE_TEST" in managed_room_manager.rooms

        # 5. Room is removed after 5 minutes total
        room._emptied_at = time.time() - (5 * 60 + 10)
        await managed_room_manager._run_cleanup()
        assert "LIFECYCLE_TEST" not in managed_room_manager.rooms
