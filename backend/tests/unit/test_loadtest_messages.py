"""The load generator's messages must pass the server's own protocol validation.

A message the server rejects never reaches the hot path the load test measures, so
the run reports zero deliveries and a knee at the first step instead of failing.
"""

from __future__ import annotations

import asyncio
import json
from collections import Counter

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from app.rooms.protocol import CLIENT_EVENT_ADAPTER
from loadtest.run import FAKE_DRAWING, Config, Player, Stats, StepResult, sent_at, start_game_message, stroke_fragment

PLAYER = "lt-1000-0"


@pytest.mark.parametrize("draw_seconds", [0.5, 4, 30])
def test_start_game_is_within_the_server_bounds(draw_seconds: float) -> None:
    """Short load-test drawing spells still send timers the server accepts."""
    CLIENT_EVENT_ADAPTER.validate_python(start_game_message(draw_seconds))


def test_stroke_fragment_is_valid_and_carries_its_send_time() -> None:
    """The fragment validates, and the receiver reads the send time back unchanged."""
    message = stroke_fragment(PLAYER, [150, 200], 12345.678901, start=True)

    event = CLIENT_EVENT_ADAPTER.validate_python(message)

    assert sent_at(event.model_dump(by_alias=True)["stroke"]) == pytest.approx(12345.678901)


@given(st.lists(st.tuples(st.integers(0, 10_000), st.integers(0, 10_000)), max_size=1000))
@example([(0, 0), (10_000, 10_000)])
def test_legacy_fragment_changes_only_point_shape(points: list[tuple[int, int]]) -> None:
    """The old protocol gets the same points and timestamp as the current workload."""
    flat = [coordinate for point in points for coordinate in point]
    current = stroke_fragment(PLAYER, flat, 12345.678901, start=True)
    legacy = stroke_fragment(PLAYER, flat, 12345.678901, start=True, legacy_wire=True)
    legacy_stroke = legacy["stroke"]
    assert isinstance(legacy_stroke, dict)
    assert [(point["x"], point["y"]) for point in legacy_stroke["points"]] == points
    assert legacy == {
        **current,
        "stroke": {"color": "t12345.678901", "width": 4, "points": legacy_stroke["points"]},
    }
    assert sent_at(legacy_stroke) == pytest.approx(12345.678901, rel=0, abs=1e-6)


@pytest.mark.parametrize("legacy_wire", [False, True])
def test_relay_measurement_counts_fragments_with_the_same_window_and_self_exclusion(*, legacy_wire: bool) -> None:
    """One old relay and one fragment in a batch each count as one delivery."""
    cfg = Config("ws://example.test", 3, 15, 4, 20, (10, 20))
    stats = Stats()
    player = Player(cfg, stats, "100000", 0, asyncio.Event())
    fragments = [
        stroke_fragment(player.player_id, [0, 0], 10.3, start=True),
        stroke_fragment("peer-one", [1, 2], 10.4, start=True),
        stroke_fragment("peer-two", [3, 4], 10.3, start=True),
    ]
    messages = fragments if legacy_wire else [{"type": "draw_stroke_batch", "fragments": fragments}]
    for message in messages:
        player.record_relay(message, 9)
        player.record_relay(message, 10.5)
        player.record_relay(message, 21)
    assert stats.latencies_ms == pytest.approx([100, 200], rel=0, abs=1e-9)


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
