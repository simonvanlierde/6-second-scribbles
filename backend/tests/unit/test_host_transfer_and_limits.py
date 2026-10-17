"""Tests for host transfer on reconnection and player limit enforcement."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from fastapi import WebSocketDisconnect

from app.core.config import settings
from app.core.rate_limits import client_network
from app.rooms import kick_vote
from app.rooms.manager import ClientRoomLimitError, GameRoom, PlayerInfo, RoomCapacityError, RoomManager, room_manager
from app.rooms.player_lifecycle import KICKED_ERROR
from tests.constants import FULL, JOIN_ERROR, ROOM_FULL
from tests.support import TestWebSocket, as_websocket

WS_TRY_AGAIN_LATER = 1013

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient

HOST_PLAYER_ID = "host_123"
SECOND_PLAYER_ID = "player_456"
PLAYER_11_ID = "player_11"
PLAYER_123_ID = "player_123"


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

        ws1_new = make_ws()
        _player, is_reconnecting = await room.add_player(HOST_PLAYER_ID, "Host Player", as_websocket(ws1_new))

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

        for i in range(10):
            await room.add_player(f"player_{i}", f"Player {i}", as_websocket(make_ws()))

        assert len(room.players) == 10

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

        await room.remove_player("player_5")
        assert len(room.players) == 9

        await room.add_player("player_10", "Player 10", as_websocket(make_ws()))
        assert len(room.players) == 10

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
            ws.receive_text()

            ws.send_text(json.dumps({"type": "join", "playerId": "player_11", "name": "Player 11"}))

            response = json.loads(ws.receive_text())
            assert response["type"] == JOIN_ERROR
            assert response["error"] == ROOM_FULL
            assert FULL in response["message"].lower()


class TestGlobalRoomCap:
    """Test suite for the global total-room cap."""

    def test_creating_room_past_cap_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_or_create_room raises once the global cap is reached."""
        monkeypatch.setattr(settings, "max_total_rooms", 1)

        room_manager.get_or_create_room("ROOM_ONE")

        with pytest.raises(RoomCapacityError):
            room_manager.get_or_create_room("ROOM_TWO")

    def test_existing_room_still_returned_at_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A room that already exists is returned even when the cap is reached."""
        monkeypatch.setattr(settings, "max_total_rooms", 1)

        first = room_manager.get_or_create_room("ROOM_ONE")
        again = room_manager.get_or_create_room("ROOM_ONE")

        assert first is again

    def test_websocket_closes_when_at_capacity(
        self,
        test_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A websocket connecting to a new room at capacity is closed with 1013."""
        monkeypatch.setattr(settings, "max_total_rooms", 0)

        with pytest.raises(WebSocketDisconnect) as exc_info, test_client.websocket_connect("/ws/NEWROOM") as ws:
            ws.receive_text()

        assert exc_info.value.code == WS_TRY_AGAIN_LATER


class TestGhostPlayerPrevention:
    """Test that persistent player IDs prevent ghost players."""

    async def test_reconnecting_player_replaces_old_connection(self, make_ws: Callable[..., TestWebSocket]) -> None:
        """Test that reconnecting with same player ID replaces old connection."""
        room_id = "RECONNECT_TEST"
        room = room_manager.get_or_create_room(room_id)

        ws1 = make_ws()
        _player1, _ = await room.add_player(PLAYER_123_ID, "Test Player", as_websocket(ws1))
        assert room.players[PLAYER_123_ID].websocket == ws1

        ws2 = make_ws()
        _player2, _ = await room.add_player(PLAYER_123_ID, "Test Player", as_websocket(ws2))

        assert PLAYER_123_ID in room.players
        assert room.players[PLAYER_123_ID].websocket == ws2
        assert len(room.players) == 1


class _StuckWebSocket(TestWebSocket):
    """A client that stopped reading: sends never complete."""

    async def send_text(self, message: str) -> None:
        del message
        await asyncio.Event().wait()


async def test_stuck_socket_does_not_hold_up_the_room(monkeypatch: pytest.MonkeyPatch) -> None:
    """A send that never completes times out, and the other players still get the message."""
    monkeypatch.setattr(settings, "ws_send_timeout_seconds", 0.05)
    room = GameRoom("STUCK01")
    stuck, healthy = _StuckWebSocket(), TestWebSocket()
    room.players["stuck"] = PlayerInfo(id="stuck", name="Stuck", websocket=as_websocket(stuck))
    room.players["ok"] = PlayerInfo(id="ok", name="Ok", websocket=as_websocket(healthy))

    await asyncio.wait_for(room.broadcast(room.room_state_event()), timeout=1)
    await asyncio.sleep(0)  # let the background close run

    assert room.players["stuck"].connected is False
    assert len(healthy.sent_texts) == 1
    assert stuck.close_calls


async def test_kicked_player_cannot_rejoin(make_ws: Callable[..., TestWebSocket]) -> None:
    """A vote-kicked player id is refused when it tries to join the same room again."""
    room = GameRoom("KICKED01")
    await room.add_player("host", "Host", as_websocket(make_ws()))
    await room.add_player("troll", "Troll", as_websocket(make_ws()), rejoin_key="troll-key")

    await kick_vote.kick_player(room, "troll")

    with pytest.raises(ValueError, match=KICKED_ERROR):
        await room.add_player("troll", "Troll", as_websocket(make_ws()), rejoin_key="troll-key")
    await room.scheduler.shutdown()


CLIENT_A = "203.0.113.7"
CLIENT_B = "198.51.100.1"
NON_IP_CLIENT = "testclient"
ROOM_A, ROOM_B, ROOM_C, ROOM_D = "AAAAAA", "BBBBBB", "CCCCCC", "DDDDDD"


def test_one_client_cannot_hold_more_than_its_share_of_rooms(monkeypatch: pytest.MonkeyPatch) -> None:
    """The room cap per client stops one network from filling the global cap; others are unaffected."""
    monkeypatch.setattr(settings, "max_rooms_per_client", 2)
    manager = RoomManager()
    manager.get_or_create_room(ROOM_A, creator=CLIENT_A)
    manager.get_or_create_room(ROOM_B, creator=CLIENT_A)

    with pytest.raises(ClientRoomLimitError):
        manager.get_or_create_room(ROOM_C, creator=CLIENT_A)
    assert manager.get_or_create_room(ROOM_A, creator=CLIENT_A).room_id == ROOM_A
    assert manager.get_or_create_room(ROOM_D, creator=CLIENT_B).room_id == ROOM_D


def test_client_network_groups_ipv6_by_64() -> None:
    """Addresses in one IPv6 /64 count as one client; IPv4 and other ids pass through."""
    assert client_network("2001:db8:1:2::1") == client_network("2001:db8:1:2:ffff::9")
    assert client_network("2001:db8:1:2::1") != client_network("2001:db8:1:3::1")
    assert client_network(CLIENT_A) == CLIENT_A
    assert client_network(NON_IP_CLIENT) == NON_IP_CLIENT
