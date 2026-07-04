"""Tests for room hibernation and automatic garbage collection."""

import time
from typing import TYPE_CHECKING

import pytest

from app.core.config import settings
from app.rooms.manager import GameRoom, RoomManager, room_manager
from tests.support import as_websocket

if TYPE_CHECKING:
    from collections.abc import Callable

    from httpx import AsyncClient

    from tests.support import TestWebSocket

EMPTY_TEST_ROOM = "EMPTY_TEST"
HIBERNATE_TEST_ROOM = "HIBERNATE_TEST"
REMOVAL_TEST_ROOM = "REMOVAL_TEST"
WAKE_TEST_ROOM = "WAKE_TEST"
CLEANUP_STATE_TEST_ROOM = "CLEANUP_STATE_TEST"
ACTIVE_ROOM = "ACTIVE_ROOM"
STATS_OK = "ok"
LIFECYCLE_TEST_ROOM = "LIFECYCLE_TEST"
PLAYER_1 = "player_1"
PLAYER_2 = "player_2"
PLAYER_3 = "player_3"
EXPECTED_HIBERNATED = "hibernated"
EXPECTED_REMOVED = "removed"


async def _run_cleanup(manager: RoomManager) -> None:
    cleanup = manager.__class__.__dict__["_run_cleanup"]
    await cleanup(manager)


class TestRoomHibernation:
    """Test suite for room hibernation functionality."""

    async def test_room_marked_empty_on_last_player_leave(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that room is marked when last player leaves."""
        room = room_manager.get_or_create_room(EMPTY_TEST_ROOM)

        ws = make_ws()
        await room.add_player(PLAYER_1, "Player 1", as_websocket(ws))
        assert not room.is_empty()
        assert room.emptied_at is None

        await room.remove_player(PLAYER_1)
        assert room.is_empty()
        assert room.emptied_at is not None

    async def test_room_enters_hibernation_after_1_minute(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that room enters hibernation after being empty for 1 minute."""
        room = GameRoom(HIBERNATE_TEST_ROOM)

        ws = make_ws()
        await room.add_player(PLAYER_1, "Player 1", as_websocket(ws))
        await room.remove_player(PLAYER_1)

        assert not room.is_hibernated
        assert not room.should_hibernate()

        # Simulate time passing past the hibernation threshold
        room.emptied_at = time.time() - (settings.room_hibernation_delay_seconds + 5)

        assert room.should_hibernate()

        room.hibernate()
        assert room.is_hibernated

    async def test_room_removed_after_5_minutes(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that room is marked for removal after 5 minutes empty."""
        room = GameRoom(REMOVAL_TEST_ROOM)

        ws = make_ws()
        await room.add_player(PLAYER_1, "Player 1", as_websocket(ws))
        await room.remove_player(PLAYER_1)

        assert not room.should_be_removed()

        room.emptied_at = time.time() - (settings.room_ttl_seconds + 10)

        assert room.should_be_removed()

    async def test_room_wakes_from_hibernation_on_join(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that hibernated room wakes up when player joins."""
        room = GameRoom(WAKE_TEST_ROOM)

        room.is_hibernated = True
        room.emptied_at = time.time() - (settings.room_hibernation_delay_seconds + 60)

        ws = make_ws()
        _player, _ = await room.add_player(PLAYER_1, "Player 1", as_websocket(ws))

        assert not room.is_hibernated
        assert room.emptied_at is None


class TestRoomManagerCleanup:
    """Test suite for RoomManager periodic cleanup."""

    async def test_room_manager_starts_and_stops(self) -> None:
        """Test that room manager can start and stop cleanly."""
        manager = RoomManager()

        await manager.start()
        assert manager.is_running

        await manager.stop()
        assert not manager.is_running

    @pytest.mark.parametrize(
        ("empty_seconds", "expected_state"),
        [
            (settings.room_hibernation_delay_seconds + 5, EXPECTED_HIBERNATED),
            (settings.room_ttl_seconds + 10, EXPECTED_REMOVED),
        ],
    )
    async def test_cleanup_state_transitions(
        self,
        managed_room_manager: RoomManager,
        make_ws: Callable[..., TestWebSocket],
        empty_seconds: int,
        expected_state: str,
    ) -> None:
        """Test periodic cleanup transitions: hibernate after 1 min, remove after 5 min."""
        room = managed_room_manager.get_or_create_room(CLEANUP_STATE_TEST_ROOM)
        ws = make_ws()
        await room.add_player(PLAYER_1, "Player 1", as_websocket(ws))
        await room.remove_player(PLAYER_1)

        room.emptied_at = time.time() - empty_seconds

        await _run_cleanup(managed_room_manager)

        if expected_state == EXPECTED_REMOVED:
            assert CLEANUP_STATE_TEST_ROOM not in managed_room_manager.rooms
        else:
            assert CLEANUP_STATE_TEST_ROOM in managed_room_manager.rooms
            assert room.is_hibernated

    async def test_cleanup_keeps_active_rooms(
        self,
        managed_room_manager: RoomManager,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Test that cleanup doesn't affect rooms with players."""
        room = managed_room_manager.get_or_create_room(ACTIVE_ROOM)
        ws = make_ws()
        await room.add_player(PLAYER_1, "Player 1", as_websocket(ws))

        await _run_cleanup(managed_room_manager)

        assert ACTIVE_ROOM in managed_room_manager.rooms
        assert not room.is_hibernated


class TestRoomManagerStats:
    """Test suite for room manager statistics."""

    async def test_get_stats_with_mixed_rooms(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test stats with active, empty, and hibernated rooms."""
        manager = RoomManager()

        # Active room with players
        active_room = manager.get_or_create_room("ACTIVE")
        ws1 = make_ws()
        await active_room.add_player(PLAYER_1, "Player 1", as_websocket(ws1))

        # Empty room (not hibernated yet)
        empty_room = manager.get_or_create_room("EMPTY")
        ws2 = make_ws()
        await empty_room.add_player(PLAYER_2, "Player 2", as_websocket(ws2))
        await empty_room.remove_player(PLAYER_2)

        # Hibernated room
        hibernated_room = manager.get_or_create_room("HIBERNATED")
        ws3 = make_ws()
        await hibernated_room.add_player(PLAYER_3, "Player 3", as_websocket(ws3))
        await hibernated_room.remove_player(PLAYER_3)
        hibernated_room.is_hibernated = True

        stats = manager.get_stats()

        assert stats.total_rooms == 3
        assert stats.active_rooms == 1
        assert stats.hibernated_rooms == 1
        assert stats.empty_rooms == 1
        assert stats.total_players == 1


class TestStatsEndpoint:
    """Test suite for /api/stats endpoint."""

    async def test_stats_endpoint_returns_stats(self, async_client: AsyncClient) -> None:
        """Test that /api/stats returns server statistics with correct structure."""
        # Baseline: no rooms
        response = await async_client.get("/api/stats")
        assert response.status_code == 200
        data_before = response.json()

        assert data_before["status"] == STATS_OK
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

    async def test_complete_room_lifecycle(
        self,
        managed_room_manager: RoomManager,
        make_ws: Callable[..., TestWebSocket],
    ) -> None:
        """Test room from creation to hibernation to removal."""
        # 1. Create room
        room = managed_room_manager.get_or_create_room(LIFECYCLE_TEST_ROOM)
        assert LIFECYCLE_TEST_ROOM in managed_room_manager.rooms

        # 2. Players join
        ws1, ws2 = make_ws(), make_ws()
        await room.add_player(PLAYER_1, "Player 1", as_websocket(ws1))
        await room.add_player(PLAYER_2, "Player 2", as_websocket(ws2))
        assert len(room.players) == 2

        # 3. Players leave
        await room.remove_player(PLAYER_1)
        await room.remove_player(PLAYER_2)
        assert room.is_empty()
        assert room.emptied_at is not None

        # 4. Room enters hibernation after 1 minute
        room.emptied_at = time.time() - 65
        await _run_cleanup(managed_room_manager)
        assert room.is_hibernated
        assert LIFECYCLE_TEST_ROOM in managed_room_manager.rooms

        # 5. Room is removed after 5 minutes total
        room.emptied_at = time.time() - (settings.room_ttl_seconds + 10)
        await _run_cleanup(managed_room_manager)
        assert LIFECYCLE_TEST_ROOM not in managed_room_manager.rooms
