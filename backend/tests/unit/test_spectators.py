"""Spectator sockets: they watch a room's broadcasts without joining it."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

import pytest

from app.core.config import settings
from app.core.types import GamePhase
from app.rooms.actions import handle_disconnect
from app.rooms.protocol import PlayerCardPayload, ReadyStatusEvent
from app.rooms.session import RoomWebSocketSession
from tests import support
from tests.constants import (
    ALICE,
    BOB,
    JOIN_ERROR,
    MEDIUM,
    PLAYER_1,
    PLAYER_2,
    PLAYER_ONE_ID,
    PLAYER_TWO_ID,
    READY_STATUS,
    ROOM_STATE,
    START_GAME,
    START_ROUND,
)
from tests.support import JoinedPlayer, joined_players, receive_json, send_json

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from app.rooms.manager import GameRoom
    from tests.support import TestWebSocket

WATCH = json.dumps({"type": "watch"})
SPY = "spy"


async def _watching(room: GameRoom) -> tuple[RoomWebSocketSession, TestWebSocket]:
    websocket = support.TestWebSocket()
    session = RoomWebSocketSession(room, support.as_websocket(websocket))
    await session.handle(WATCH)
    return session, websocket


def _types(websocket: TestWebSocket) -> list[str]:
    return [json.loads(text)["type"] for text in websocket.sent_texts]


async def test_watch_registers_observer_and_sends_snapshot(room_with_players: GameRoom) -> None:
    """A watcher gets a room_state but is not a player."""
    session, websocket = await _watching(room_with_players)

    assert session.is_observer
    assert len(room_with_players.observers) == 1
    assert set(room_with_players.players) == {PLAYER_ONE_ID, PLAYER_TWO_ID}
    assert _types(websocket) == [ROOM_STATE]
    assert json.loads(websocket.sent_texts[0])["totalPlayers"] == 2


async def test_observer_receives_broadcasts(room_with_players: GameRoom) -> None:
    """Room broadcasts reach spectators as well as players."""
    _session, websocket = await _watching(room_with_players)

    await room_with_players.broadcast(ReadyStatusEvent(readyCount=1, totalPlayers=2))

    assert _types(websocket)[-1] == READY_STATUS


async def test_observer_never_receives_a_card(room_with_players: GameRoom) -> None:
    """Spectators get start_round without anyone's prompts."""
    _session, websocket = await _watching(room_with_players)
    card = PlayerCardPayload(category="Animals", items=["cat"])

    await room_with_players.send_round_start(1, {PLAYER_ONE_ID: card, PLAYER_TWO_ID: card}, 1000)

    start_round = json.loads(websocket.sent_texts[-1])
    assert start_round["type"] == START_ROUND
    assert start_round["cards"] == {}
    assert json.loads(websocket.sent_texts[0]).get("card") is None


async def test_observer_cannot_play(room_with_players: GameRoom) -> None:
    """Game actions from a spectator are refused, host-only ones included."""
    room_with_players.host_id = None
    session, websocket = await _watching(room_with_players)

    await session.handle(json.dumps({"type": START_GAME, "difficulty": MEDIUM}))
    await session.handle(json.dumps({"type": "join", "playerId": SPY, "name": "Spy"}))

    assert _types(websocket)[1:] == ["permission_error", "permission_error"]
    assert SPY not in room_with_players.players
    assert room_with_players.metadata.game_phase == GamePhase.LOBBY


async def test_observer_removed_on_disconnect(room_with_players: GameRoom) -> None:
    """A dropped spectator socket is forgotten and nobody is told."""
    session, _websocket = await _watching(room_with_players)

    await handle_disconnect(session)

    assert room_with_players.observers == []
    assert set(room_with_players.players) == {PLAYER_ONE_ID, PLAYER_TWO_ID}


async def test_observer_cap(room_with_players: GameRoom, monkeypatch: pytest.MonkeyPatch) -> None:
    """Past the per-room cap a watcher gets a join_error and a policy close."""
    monkeypatch.setattr(settings, "max_observers", 1)
    await _watching(room_with_players)

    session, websocket = await _watching(room_with_players)

    assert not session.is_observer
    assert len(room_with_players.observers) == 1
    assert json.loads(websocket.sent_texts[-1]) == {
        "type": JOIN_ERROR,
        "error": "spectators_full",
        "message": "This room has as many spectators as it allows.",
    }
    assert websocket.close_calls[-1]["code"] == 1008


@pytest.mark.usefixtures("dealt_cards")
def test_observer_follows_a_game_over_the_socket(test_client: TestClient) -> None:
    """Over a real socket, a watcher sees the game start without seeing any card."""
    with (
        joined_players(
            test_client,
            "WATCH1",
            [JoinedPlayer(PLAYER_1, ALICE), JoinedPlayer(PLAYER_2, BOB)],
        ) as (ws1, ws2),
        test_client.websocket_connect("/ws/WATCH1") as watcher,
    ):
        receive_json(watcher)  # connect-time room_state
        send_json(watcher, {"type": "watch"})
        assert receive_json(watcher)["type"] == ROOM_STATE

        send_json(ws1, {"type": START_GAME, "difficulty": MEDIUM, "rounds": 1, "drawingTimeLimit": 15})
        for socket in (ws1, ws2):
            receive_json(socket)
            receive_json(socket)

        assert receive_json(watcher)["type"] == START_GAME
        start_round = receive_json(watcher)
        assert start_round["type"] == START_ROUND
        assert cast("dict[str, object]", start_round["cards"]) == {}
