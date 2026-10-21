"""Benchmarks of the lobby doodle's per-fragment server work, measured by CodSpeed on every PR.

A plain `pytest` run calls each one once as a test; `pytest --codspeed` measures them.
They cover only work in this process: uvicorn and websockets framing stay with
`just loadtest-ab` (see docs/capacity.md).
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from app.rooms.manager import MAX_LOBBY_STROKES, GameRoom
from app.rooms.player_lifecycle import PlayerInfo
from app.rooms.protocol import (
    DrawStrokeBatchServerEvent,
    DrawStrokePartialEvent,
    StrokeDelta,
    StrokeFragment,
    encode_ws_message,
    parse_client_event,
)

# Renamed, or pytest tries to collect it as a test class.
from tests.support import TestWebSocket as FakeWebSocket
from tests.support import as_websocket

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

PLAYERS = 6
# A 50 ms send interval at a 120 Hz pointer: about 6 points per fragment.
POINTS = [coordinate for i in range(6) for coordinate in (1000 + i * 37, 2000 + i * 53)]


def _fragment(player: int) -> StrokeFragment:
    return StrokeFragment(
        player_id=f"player-{player}",
        stroke=StrokeDelta(color="#2d2d2d", width=6, points=POINTS),
        stroke_start=False,
    )


def _batch() -> DrawStrokeBatchServerEvent:
    """One tick of a room where every player is drawing."""
    return DrawStrokeBatchServerEvent(fragments=[_fragment(i) for i in range(PLAYERS)])


def test_parse_draw_stroke_partial(benchmark: BenchmarkFixture) -> None:
    """Validate one incoming stroke fragment."""
    raw = json.dumps(
        {
            "type": "draw_stroke_partial",
            "playerId": "player-0",
            "stroke": {"color": "#2d2d2d", "width": 6, "points": POINTS},
            "strokeStart": False,
        }
    )

    event = benchmark(parse_client_event, raw)

    assert isinstance(event, DrawStrokePartialEvent)


def test_encode_draw_stroke_batch(benchmark: BenchmarkFixture) -> None:
    """Serialize one tick's batch, once for all recipients."""
    batch = _batch()

    text = benchmark(encode_ws_message, batch)

    assert text.startswith('{"type":"draw_stroke_batch"')


def test_broadcast_batch_to_six_players(benchmark: BenchmarkFixture) -> None:
    """Fan one batch out to six connections."""
    room = GameRoom("BENCH1")
    sockets = [FakeWebSocket() for _ in range(PLAYERS)]
    for i, socket in enumerate(sockets):
        room.players[f"player-{i}"] = PlayerInfo(id=f"player-{i}", name=f"P{i}", websocket=as_websocket(socket))
    batch = _batch()

    # NOTE: includes the event loop's cost of running one coroutine.
    with asyncio.Runner() as runner:
        benchmark(lambda: runner.run(room.broadcast(batch)))

    assert all(socket.sent_texts for socket in sockets)


def test_new_lobby_stroke_on_a_full_doodle(benchmark: BenchmarkFixture) -> None:
    """Store a new stroke when the doodle already holds the most it keeps."""
    room = GameRoom("BENCH1")
    # Each new stroke trims the oldest; at 6 points a stroke the point cap is far off.
    for i in range(MAX_LOBBY_STROKES):
        room.apply_lobby_partial(
            f"player-{i % PLAYERS}", StrokeDelta(color="#2d2d2d", width=6, points=POINTS), is_start=True
        )
    fragment = StrokeDelta(color="#2d2d2d", width=6, points=POINTS)

    benchmark(room.apply_lobby_partial, "player-0", fragment, is_start=True)

    assert len(room.lobby_strokes) == MAX_LOBBY_STROKES
