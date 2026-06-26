"""Tests for the per-connection inbound draw-event throttle."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from app.core.config import settings
from app.rooms.session import RoomWebSocketSession
from tests.constants import PLAYER_ONE_ID
from tests.support import as_websocket

if TYPE_CHECKING:
    import pytest

    from app.rooms.manager import GameRoom
    from tests.support import TestWebSocket

DRAW_PAYLOAD = json.dumps(
    {
        "type": "draw_stroke",
        "playerId": PLAYER_ONE_ID,
        "stroke": {"color": "#000000", "width": 2, "points": [{"x": 1, "y": 2}]},
    },
)
CONTROL_PAYLOAD = json.dumps({"type": "request_game_state"})


async def test_draw_strokes_dropped_past_window_limit(
    game_room: GameRoom,
    mock_websocket: TestWebSocket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the allowed number of draw strokes per window are broadcast; the rest are dropped."""
    monkeypatch.setattr(settings, "ws_draw_messages_per_window", 2)
    monkeypatch.setattr(settings, "ws_draw_window_seconds", 1)
    broadcast = AsyncMock()
    monkeypatch.setattr(game_room, "broadcast", broadcast)
    session = RoomWebSocketSession(game_room, as_websocket(mock_websocket))

    for _ in range(3):
        await session.handle(DRAW_PAYLOAD)

    assert broadcast.await_count == 2


async def test_control_events_not_throttled(
    game_room: GameRoom,
    mock_websocket: TestWebSocket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Control events still dispatch even when the draw limit is exhausted."""
    monkeypatch.setattr(settings, "ws_draw_messages_per_window", 0)
    monkeypatch.setattr(settings, "ws_draw_window_seconds", 1)
    session = RoomWebSocketSession(game_room, as_websocket(mock_websocket))

    # Draw is dropped (limit is 0), so nothing is broadcast for it...
    await session.handle(DRAW_PAYLOAD)
    # ...but a control event still produces a room_state response on the socket.
    sent_before = len(mock_websocket.sent_texts)
    await session.handle(CONTROL_PAYLOAD)

    assert len(mock_websocket.sent_texts) == sent_before + 1
