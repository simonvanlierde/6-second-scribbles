"""The load generator's messages must pass the server's own protocol validation.

A message the server rejects never reaches the hot path the load test measures, so
the run reports zero deliveries and a knee at the first step instead of failing.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from app.rooms.protocol import CLIENT_EVENT_ADAPTER
from loadtest.run import FAKE_DRAWING, StepResult, sent_at, start_game_message, stroke_fragment

PLAYER = "lt-1000-0"


@pytest.mark.parametrize("draw_seconds", [0.5, 4, 30])
def test_start_game_is_within_the_server_bounds(draw_seconds: float) -> None:
    """Short load-test drawing spells still send timers the server accepts."""
    CLIENT_EVENT_ADAPTER.validate_python(start_game_message(draw_seconds))


def test_stroke_fragment_is_valid_and_carries_its_send_time() -> None:
    """The fragment validates, and the receiver reads the send time back unchanged."""
    message = stroke_fragment(PLAYER, [{"x": 1.5, "y": 2.0}], 12345.678901, start=True)

    event = CLIENT_EVENT_ADAPTER.validate_python(message)

    assert sent_at(event.model_dump(by_alias=True)["stroke"]) == pytest.approx(12345.678901)


def test_the_other_bot_messages_are_valid() -> None:
    """Every other message the bots send passes validation too."""
    for message in (
        {"type": "join", "playerId": PLAYER, "name": "Bot 1"},
        {"type": "draw_stroke", "playerId": PLAYER, "drawing": FAKE_DRAWING},
        {"type": "player_ready", "playerId": PLAYER},
        {"type": "submit_guess", "playerId": PLAYER, "targetPlayerId": "lt-1000-1", "guesses": ["cat"]},
        {"type": "restart_game"},
        {"type": "leave"},
    ):
        CLIENT_EVENT_ADAPTER.validate_python(message)


def test_a_step_with_errors_serializes_to_json() -> None:
    """`--json` keeps the error counts, which `ab.py` reads back."""
    errors: Counter[str] = Counter({"disconnect": 2})
    step = StepResult(
        rooms=40,
        players=6,
        p50_ms=1.0,
        p95_ms=2.0,
        deliveries_per_s=100.0,
        cpu_pct=50.0,
        mem_mib=150.0,
        errors=errors,
        rounds_scored=3,
        generator_cpu_pct=30.0,
    )
    assert json.loads(json.dumps(step.as_json()))["errors"] == {"disconnect": 2}
