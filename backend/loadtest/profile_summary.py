"""Summarize py-spy raw (collapsed) stacks into self and inclusive time per function.

``just profile`` runs this on the file ``py-spy record --format raw`` writes::

    uv run python -m loadtest.profile_summary stacks.txt --top 20
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

LINE_NUMBER = re.compile(r":\d+\)$")


def summarize(lines: list[str]) -> tuple[Counter[str], Counter[str], int]:
    """Return (self samples, inclusive samples, total samples) per function.

    Each line is ``frame;frame;...;leaf count``, root first. Line numbers are dropped
    so every line of a function counts towards the function. A function that appears
    twice in one stack (recursion) counts once towards its inclusive total.
    """
    self_counts: Counter[str] = Counter()
    inclusive: Counter[str] = Counter()
    total = 0
    for line in lines:
        stack, _, count_text = line.strip().rpartition(" ")
        if not stack or not count_text.isdigit():
            continue
        count = int(count_text)
        frames = [LINE_NUMBER.sub(")", frame) for frame in stack.split(";")]
        total += count
        self_counts[frames[-1]] += count
        for frame in set(frames):
            inclusive[frame] += count
    return self_counts, inclusive, total


def table(title: str, counts: Counter[str], total: int, top: int) -> str:
    """One ranked table of the busiest functions."""
    rows = [f"{title} (share of {total} samples)"]
    rows += [f"{n / total:6.1%} {n:>7}  {name}" for name, n in counts.most_common(top)]
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    """Print the self and inclusive tables for a raw stacks file."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stacks", type=Path, help="file from `py-spy record --format raw`")
    parser.add_argument("--top", type=int, default=15, help="rows per table")
    args = parser.parse_args(argv)
    self_counts, inclusive, total = summarize(args.stacks.read_text(encoding="utf-8").splitlines())
    if total == 0:
        print(f"No samples in {args.stacks}")  # noqa: T201
        return 1
    print(table("Self time", self_counts, total, args.top))  # noqa: T201
    print()  # noqa: T201
    print(table("Inclusive time", inclusive, total, args.top))  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
