"""Tests for the per-connection inbound draw-event throttle."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.config import settings
from app.rooms.manager import MAX_LOBBY_POINTS
from app.rooms.protocol import StrokeDelta, StrokePoint, encode_ws_message, parse_client_event
from app.rooms.session import RoomWebSocketSession
from tests.constants import PLAYER_ONE_ID
from tests.support import as_websocket

if TYPE_CHECKING:
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
    session.player_id = PLAYER_ONE_ID

    for _ in range(3):
        await session.handle(DRAW_PAYLOAD)

    assert broadcast.await_count == 2


async def test_draw_strokes_from_unjoined_socket_are_dropped(
    game_room: GameRoom,
    mock_websocket: TestWebSocket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A socket that has not joined cannot relay drawings to the room."""
    broadcast = AsyncMock()
    monkeypatch.setattr(game_room, "broadcast", broadcast)
    session = RoomWebSocketSession(game_room, as_websocket(mock_websocket))

    await session.handle(DRAW_PAYLOAD)

    broadcast.assert_not_awaited()


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


async def test_game_state_requests_dropped_past_window_limit(
    game_room: GameRoom,
    mock_websocket: TestWebSocket,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each room_state carries every drawing, so a socket gets only a few per window."""
    monkeypatch.setattr(settings, "ws_state_requests_per_window", 2)
    monkeypatch.setattr(settings, "ws_state_window_seconds", 60)
    session = RoomWebSocketSession(game_room, as_websocket(mock_websocket))

    for _ in range(4):
        await session.handle(CONTROL_PAYLOAD)

    assert len(mock_websocket.sent_texts) == 2


def test_lobby_doodle_stays_small_under_maximum_fragments(game_room: GameRoom) -> None:
    """600 maximum-size fragments keep the doodle under the point cap and room_state under 1 MB."""
    fragment = StrokeDelta(color="#000000", width=2, points=[StrokePoint(x=i, y=i) for i in range(1000)])

    for _ in range(600):
        game_room.apply_lobby_partial(PLAYER_ONE_ID, fragment, is_start=True)

    assert sum(len(stroke.points) for stroke in game_room.lobby_strokes) <= MAX_LOBBY_POINTS
    assert len(encode_ws_message(game_room.room_state_event())) < 1_000_000


def test_oversized_fields_are_rejected() -> None:
    """Names, ids and stroke styles have upper bounds, so one message cannot bloat every room_state."""
    too_long = [
        {"type": "join", "playerId": PLAYER_ONE_ID, "name": "x" * 81},
        {"type": "join", "playerId": "x" * 65, "name": "Alice"},
        {"type": "draw_stroke_partial", "stroke": {"color": "x" * 33, "width": 2, "points": []}},
        {"type": "draw_stroke_partial", "stroke": {"color": "#000", "width": 1000, "points": []}},
    ]
    for payload in too_long:
        with pytest.raises(ValidationError):
            parse_client_event(json.dumps(payload))
