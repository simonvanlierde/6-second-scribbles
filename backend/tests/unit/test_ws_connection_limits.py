"""Admission bounds include connections still resolving authentication."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from app.core.config import settings
from app.rooms import ws_router
from app.rooms.manager import GameRoom

if TYPE_CHECKING:
    import pytest
    from pytest_mock import MockerFixture


def configure_endpoint(mocker: MockerFixture, room: GameRoom) -> AsyncMock:
    """Keep endpoint admission real while replacing database and session work."""
    manager = mocker.Mock()
    manager.get_room.return_value = room
    manager.get_or_create_room.return_value = room
    mocker.patch.object(ws_router, "room_manager", manager)
    database = AsyncMock()
    database.__aenter__.return_value = database
    mocker.patch.object(ws_router, "get_session_maker", return_value=lambda: database)
    mocker.patch.object(ws_router, "RoomWebSocketSession", return_value=AsyncMock())
    return mocker.patch.object(ws_router, "get_user_by_session", new=AsyncMock(return_value=None))


def websocket() -> AsyncMock:
    """Create a socket with ordinary request metadata."""
    socket = AsyncMock()
    socket.cookies = {}
    socket.headers = {}
    socket.client = None
    return socket


async def test_admission_rejects_room_at_connection_capacity(mocker: MockerFixture) -> None:
    """Reconnect capacity is finite even when player seats remain empty."""
    room = GameRoom("CAP001")
    room.active_connections = 2 * settings.max_players + settings.max_observers
    auth = configure_endpoint(mocker, room)
    socket = websocket()

    await ws_router.websocket_endpoint(socket, "CAP001")

    socket.close.assert_awaited_once_with(code=1013, reason="Too many room connections")
    auth.assert_not_awaited()
    assert room.active_connections == 2 * settings.max_players + settings.max_observers


async def test_pending_authentication_occupies_admission_slot(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent handshakes cannot all pass a cap before authentication finishes."""
    monkeypatch.setattr(settings, "max_players", 1)
    monkeypatch.setattr(settings, "max_observers", 0)
    room = GameRoom("CAP002")
    auth = configure_endpoint(mocker, room)
    release = asyncio.Event()
    entered = asyncio.Event()
    count = 0

    async def authenticate(*_args: object) -> None:
        nonlocal count
        count += 1
        if count == 2:
            entered.set()
        await release.wait()

    auth.side_effect = authenticate
    sockets = [websocket() for _ in range(3)]
    tasks = [asyncio.create_task(ws_router.websocket_endpoint(socket, "CAP002")) for socket in sockets[:2]]
    try:
        await asyncio.wait_for(entered.wait(), timeout=1)
        await ws_router.websocket_endpoint(sockets[2], "CAP002")
        sockets[2].close.assert_awaited_once_with(code=1013, reason="Too many room connections")
        assert room.active_connections == 2
    finally:
        release.set()
        await asyncio.gather(*tasks)
    assert room.active_connections == 0


async def test_authentication_failure_releases_admission_slot(mocker: MockerFixture) -> None:
    """Database setup failures do not permanently exhaust room connections."""
    room = GameRoom("CAP003")
    auth = configure_endpoint(mocker, room)
    auth.side_effect = RuntimeError("database unavailable")
    socket = websocket()

    await ws_router.websocket_endpoint(socket, "CAP003")

    assert room.active_connections == 0
    socket.close.assert_awaited_once_with(code=1011, reason="Connection setup failed")
