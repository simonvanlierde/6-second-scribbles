"""Benchmarks for websocket message parsing and encoding (run for every frame)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.rooms.protocol import (
    DrawStrokeBatchServerEvent,
    RoundCompleteServerEvent,
    RoundResultItem,
    StrokeDelta,
    StrokeFragment,
    encode_ws_message,
    parse_client_event,
)

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture

PLAYER_IDS = [f"player-{i}" for i in range(8)]

JOIN_PAYLOAD = json.dumps(
    {"type": "join", "playerId": PLAYER_IDS[0], "name": "Alice", "preferredLocale": "en", "rejoinKey": "k" * 32},
)
SUBMIT_GUESS_PAYLOAD = json.dumps(
    {
        "type": "submit_guess",
        "playerId": PLAYER_IDS[0],
        "targetPlayerId": PLAYER_IDS[1],
        "guesses": ["elephant", "giraffe", "tiger", "new york", "ice cream", "coffee"],
    },
)
STROKE_PARTIAL_PAYLOAD = json.dumps(
    {
        "type": "draw_stroke_partial",
        "playerId": PLAYER_IDS[0],
        "stroke": {"color": "#ff8800", "width": 4.0, "points": [i % 10_000 for i in range(400)]},
    },
)


def test_parse_join_event(benchmark: BenchmarkFixture) -> None:
    """Parse a raw join frame."""
    benchmark(parse_client_event, JOIN_PAYLOAD)


def test_parse_submit_guess_event(benchmark: BenchmarkFixture) -> None:
    """Parse a raw guess submission frame."""
    benchmark(parse_client_event, SUBMIT_GUESS_PAYLOAD)


def test_parse_draw_stroke_partial_event(benchmark: BenchmarkFixture) -> None:
    """Parse a lobby doodle fragment with 200 points (the most frequent frame)."""
    benchmark(parse_client_event, STROKE_PARTIAL_PAYLOAD)


def test_encode_draw_stroke_batch(benchmark: BenchmarkFixture) -> None:
    """Encode one tick's batch of doodle fragments from every player."""
    event = DrawStrokeBatchServerEvent(
        fragments=[
            StrokeFragment(
                playerId=player_id,
                stroke=StrokeDelta(color="#123456", width=3.5, points=[(i * 7) % 10_000 for i in range(100)]),
                strokeStart=False,
            )
            for player_id in PLAYER_IDS
        ],
    )
    benchmark(encode_ws_message, event)


def test_encode_round_complete(benchmark: BenchmarkFixture) -> None:
    """Encode the round results broadcast."""
    event = RoundCompleteServerEvent(
        results=[
            RoundResultItem(
                playerId=player_id,
                targetPlayerId=PLAYER_IDS[(i + 1) % len(PLAYER_IDS)],
                correctGuesses=i % 6,
                totalItems=6,
                pointsEarned=i % 6,
            )
            for i, player_id in enumerate(PLAYER_IDS)
        ],
        scores={player_id: i * 3 for i, player_id in enumerate(PLAYER_IDS)},
    )
    benchmark(encode_ws_message, event)
