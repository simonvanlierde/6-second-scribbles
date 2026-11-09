"""The profile summary splits self time from inclusive time."""

from __future__ import annotations

from loadtest.profile_summary import summarize


def test_self_and_inclusive_counts() -> None:
    """A caller's inclusive time covers the functions it calls; only the leaf gets self time."""
    lines = [
        "main (a.py:1);work (a.py:5);leaf (b.py:9) 3",
        "main (a.py:1);work (a.py:6) 2",
        "main (a.py:2);work (a.py:5);work (a.py:5) 1",
        "not a stack line",
    ]

    self_counts, inclusive, total = summarize(lines)

    assert total == 6
    assert self_counts == {"leaf (b.py)": 3, "work (a.py)": 3}
    assert inclusive["main (a.py)"] == 6
    assert inclusive["work (a.py)"] == 6  # the recursive stack counts once
    assert inclusive["leaf (b.py)"] == 3
