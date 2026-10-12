"""Tests for the load-test harness's statistics helpers."""

from __future__ import annotations

import math
from collections import Counter

import pytest

from loadtest.run import Stats, is_knee, parse_mem_mib, percentile


def test_percentile_nearest_rank() -> None:
    """Percentiles pick an observed sample by nearest rank, regardless of input order."""
    values = [float(v) for v in range(1, 101)]
    assert percentile(values, 50) == values[49]
    assert percentile(values, 95) == values[94]
    assert percentile(values, 100) == values[-1]
    assert percentile([7], 95) == 7
    assert percentile([3, 1, 2], 50) == 2


def test_percentile_empty_is_nan() -> None:
    """No samples gives NaN, not an exception."""
    assert math.isnan(percentile([], 50))


@pytest.mark.parametrize(
    ("usage", "expected"),
    [
        ("123.5MiB / 1GiB", 123.5),
        ("1.5GiB / 2GiB", 1536),
        ("512KiB / 1GiB", 0.5),
    ],
)
def test_parse_mem_mib(usage: str, expected: float) -> None:
    """The used half of docker stats MemUsage is converted to MiB."""
    assert parse_mem_mib(usage) == pytest.approx(expected)


def test_parse_mem_mib_rejects_unknown_unit() -> None:
    """An unknown unit fails loudly instead of reporting a wrong number."""
    with pytest.raises(ValueError, match="Unrecognised"):
        parse_mem_mib("12TB / 1GiB")


def test_is_knee() -> None:
    """A step degrades on high p95, any error, or no deliveries at all."""
    assert not is_knee(100, 0, 250)
    assert is_knee(251, 0, 250)
    assert is_knee(10, 1, 250)
    assert is_knee(math.nan, 0, 250)


def test_stats_merge() -> None:
    """Merging sums counters and keeps the busiest worker's CPU share."""
    a = Stats(latencies_ms=[1], rounds_scored=1, errors=Counter(disconnect=1), cpu_share=0.2)
    b = Stats(latencies_ms=[2, 3], rounds_scored=2, errors=Counter(disconnect=1, connect_failed=1), cpu_share=0.5)
    a.merge(b)
    assert a.latencies_ms == [1, 2, 3]
    assert a.rounds_scored == 3
    assert a.errors == Counter(disconnect=2, connect_failed=1)
    assert a.cpu_share == b.cpu_share
