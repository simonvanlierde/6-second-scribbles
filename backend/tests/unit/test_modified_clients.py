"""Regressions for messages forged by modified game clients."""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.types import GamePhase
from app.rooms import player_lifecycle, rounds
from app.rooms.protocol import parse_client_event
from app.rooms.session import RoomWebSocketSession
from tests.support import TestWebSocket as SocketDouble
from tests.support import as_websocket

HOST = "host"
ORIGINAL = "original"
NEW = "new"

if TYPE_CHECKING:
    from app.rooms.manager import GameRoom


async def joined_session(room: GameRoom, player_id: str = "host") -> RoomWebSocketSession:
    """Bind a real room player to its session socket."""
    socket = SocketDouble()
    await player_lifecycle.add_player(room, player_id, player_id, as_websocket(socket), rejoin_key="secret")
    session = RoomWebSocketSession(room, as_websocket(socket))
    session.player_id = player_id
    return session


async def test_replaced_socket_cannot_change_settings_or_remove_live_player(game_room: GameRoom) -> None:
    """A reconnect revokes the previous socket's permissions immediately."""
    stale = await joined_session(game_room)
    replacement = SocketDouble()
    await player_lifecycle.add_player(
        game_room,
        "host",
        "host",
        as_websocket(replacement),
        rejoin_key="secret",
    )
    original = game_room.metadata.max_rounds

    await stale.handle(json.dumps({"type": "settings_update", "rounds": 9}))
    await stale.handle(json.dumps({"type": "leave"}))

    assert game_room.metadata.max_rounds == original
    assert game_room.players["host"].websocket is as_websocket(replacement)


async def test_join_cannot_change_identity_on_same_socket(game_room: GameRoom) -> None:
    """Joining twice cannot leave an unreachable first player behind."""
    session = await joined_session(game_room)

    await session.handle(json.dumps({"type": "join", "playerId": "other", "name": "Other"}))

    assert set(game_room.players) == {"host"}
    assert session.player_id == HOST


async def test_leave_clears_session_identity(game_room: GameRoom) -> None:
    """Explicit leave also revokes authority on the still-open socket."""
    session = await joined_session(game_room)
    await session.handle(json.dumps({"type": "leave"}))
    assert session.player_id is None
    assert not session.is_host()
    assert HOST not in game_room.players


@pytest.mark.parametrize("phase", [GamePhase.GUESSING, GamePhase.ROUND_RESULTS, GamePhase.FINAL_RESULTS])
async def test_png_cannot_change_after_drawing(game_room: GameRoom, phase: GamePhase) -> None:
    """Guessers and gallery viewers cannot replace a completed drawing."""
    session = await joined_session(game_room)
    game_room.metadata.game_phase = phase
    game_room.round_drawings["host"] = "original"

    await session.handle(json.dumps({"type": "draw_stroke", "drawing": "forged"}))

    assert game_room.round_drawings["host"] == ORIGINAL


@pytest.mark.parametrize(("elapsed", "accepted"), [(31, True), (40, False)])
async def test_drawing_deadline_has_bounded_delivery_grace(
    game_room: GameRoom,
    elapsed: int,
    *,
    accepted: bool,
) -> None:
    """A late timer callback does not give the client unlimited drawing time."""
    session = await joined_session(game_room)
    game_room.metadata.game_phase = GamePhase.DRAWING
    game_room.metadata.drawing_time_limit = 30
    game_room.metadata.round_start_time = int((time.time() - elapsed) * 1000)

    await session.handle(json.dumps({"type": "draw_stroke", "drawing": "new"}))

    assert (game_room.round_drawings.get("host") == NEW) is accepted


@pytest.mark.parametrize("phase", list(GamePhase))
def test_guess_is_only_recorded_during_guessing(game_room: GameRoom, phase: GamePhase) -> None:
    """Client messages cannot bypass the server's round phase."""
    game_room.metadata.game_phase = phase
    game_room.metadata.guess_targets = {"host": "other"}
    game_room.metadata.guessing_start_time = int(time.time() * 1000)

    rounds.record_guess_submission(game_room, player_id="host", target_player_id="other", guesses=["cat"])

    assert bool(game_room.metadata.guess_submissions) is (phase == GamePhase.GUESSING)


@pytest.mark.parametrize(("elapsed", "accepted"), [(61, True), (70, False)])
def test_guess_deadline_has_bounded_delivery_grace(game_room: GameRoom, elapsed: int, *, accepted: bool) -> None:
    """Guess submission cannot outlive the scoring deadline indefinitely."""
    game_room.metadata.game_phase = GamePhase.GUESSING
    game_room.metadata.guessing_time_limit = 60
    game_room.metadata.guessing_start_time = int((time.time() - elapsed) * 1000)
    game_room.metadata.guess_targets = {"host": "other"}

    rounds.record_guess_submission(game_room, player_id="host", target_player_id="other", guesses=["cat"])

    assert bool(game_room.metadata.guess_submissions) is accepted


@pytest.mark.parametrize("phase", [GamePhase.DRAWING, GamePhase.GUESSING, GamePhase.ROUND_RESULTS])
async def test_host_cannot_change_active_round_settings(game_room: GameRoom, phase: GamePhase) -> None:
    """Even the host cannot rewrite the timer, scoring difficulty or language mid-game."""
    session = await joined_session(game_room)
    game_room.metadata.game_phase = phase
    previous = game_room.metadata.model_dump()

    await session.handle(json.dumps({"type": "settings_update", "rounds": 9, "difficulty": "hard"}))
    await session.handle(json.dumps({"type": "default_locale_update", "locale": "es"}))

    assert game_room.metadata.max_rounds == previous["max_rounds"]
    assert game_room.metadata.difficulty == previous["difficulty"]
    assert game_room.metadata.default_locale == previous["default_locale"]


def test_guess_payload_accepts_ten_guesses_but_rejects_eleven() -> None:
    """Bound synchronous scoring work while preserving the full card size."""
    payload = {"type": "submit_guess", "playerId": "host", "targetPlayerId": "other", "guesses": ["cat"] * 10}
    parse_client_event(json.dumps(payload))
    payload["guesses"] = ["cat"] * 11
    with pytest.raises(ValidationError):
        parse_client_event(json.dumps(payload))


async def test_heartbeat_does_not_extend_unjoined_timeout(game_room: GameRoom, monkeypatch: pytest.MonkeyPatch) -> None:
    """Messages before join cannot keep a connection admission slot forever."""
    monkeypatch.setattr("app.rooms.session.CONNECTION_JOIN_TIMEOUT_SECONDS", 0.03)
    socket = AsyncMock()

    async def heartbeat() -> str:
        await asyncio.sleep(0.005)
        return json.dumps({"type": "heartbeat"})

    socket.receive_text.side_effect = heartbeat
    session = RoomWebSocketSession(game_room, socket)
    await asyncio.wait_for(session.run(), timeout=0.3)
    socket.close.assert_awaited_once()
