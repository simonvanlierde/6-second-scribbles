"""CPU split for the A/B load-test script."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loadtest import ab

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

# This host: cores pair CPUs (0,8), (1,9), (2,10), (3,11), (4,12), (5,13), (6,14), (7,15).
ALLOWED = ab.parse_cpu_list("0-3,5-8,10-12,15")


def sibling_of(cpu: int) -> list[int]:
    """The hyperthread pairs of an 8-core, 16-thread CPU."""
    return sorted({cpu % 8, cpu % 8 + 8})


def test_parse_cpu_list() -> None:
    """Ranges and single CPUs both expand."""
    assert ALLOWED == [0, 1, 2, 3, 5, 6, 7, 8, 10, 11, 12, 15]


def test_split_keeps_backend_and_generator_on_separate_idle_cores(monkeypatch: pytest.MonkeyPatch) -> None:
    """The backend and each generator CPU get a core whose sibling no one else uses."""
    monkeypatch.setattr(ab, "siblings", sibling_of)
    backend, generator, rest = ab.split_cpus(ALLOWED)
    # Whole cores first: 0/8, 2/10, 3/11 and 7/15 are fully allowed.
    assert backend == 0
    assert generator == [2, 3, 7]
    assert {8, 10, 11, 15}.isdisjoint(rest)  # siblings stay idle
    assert backend not in rest
    assert not set(generator) & set(rest)
    assert rest == [1, 5, 6, 12]


def test_split_without_hyperthreads(monkeypatch: pytest.MonkeyPatch) -> None:
    """With two CPUs and no siblings, the database shares the generator's CPU."""
    monkeypatch.setattr(ab, "siblings", lambda cpu: [cpu])
    assert ab.split_cpus([4, 5]) == (4, [5], [5])


def test_legacy_wire_is_selected_per_side() -> None:
    """Only the explicitly selected side uses the old server's wire format."""
    args, extra = ab.parse_args(["v0.3.0", "HEAD", "--legacy-wire-a", "--rooms", "40", "--runs", "3"])
    assert args.legacy_wire_a is True
    assert args.legacy_wire_b is False
    assert extra == ["--duration", "20"]


def test_generator_receives_only_its_stacks_wire_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A legacy side passes the adapter flag; a current side leaves the workload alone."""
    commands: list[list[str]] = []

    def record_command(command: list[str], **_kwargs: object) -> None:
        commands.append(command)

    monkeypatch.setattr(ab.subprocess, "run", record_command)
    out = tmp_path / "results.json"
    out.write_text("[]")
    rooms, legacy_flag = "40", "--legacy-wire"
    for legacy_wire in (False, True):
        stack = ab.Stack("A", "v0.3.0", tmp_path, tmp_path / "override.yml", 18100, legacy_wire=legacy_wire)
        ab.run_generator(stack, [2, 3], rooms, ["--duration", "20"], out)
        assert (legacy_flag in commands[-1]) == legacy_wire
        assert commands[-1][commands[-1].index("--rooms") + 1] == rooms
