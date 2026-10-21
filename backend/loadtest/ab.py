"""Compare the room server's capacity at two commits: ``just loadtest-ab <ref-a> <ref-b>``.

Each ref is checked out into a detached worktree in a temporary
directory and run as the prod-limited stack from ``just loadtest``. The load generator always
comes from this checkout (``backend/loadtest/`` is also copied into each worktree for
its compose override), so old servers are measured with today's generator.

Runs alternate A, B, A, B... so slow drift in host load hits both refs alike. CPUs
are split so the two sides do not compete:

- The backend container gets one CPU (``cpuset``) on a physical core whose other
  hyperthread is left idle, and keeps the prod limit of 1.0 CPU.
- The load generator runs under ``taskset`` on up to three other cores, one process
  per CPU, again on cores whose sibling stays idle where the allowed set permits.
- Postgres and Redis get the allowed CPUs left over.

All three come from this process's ``Cpus_allowed_list``, since a session may be
fenced to part of the host and taskset silently drops CPUs outside it.

Any errored run (errors, or no deliveries at a step) or a ref whose stack does not
come up makes the command exit non-zero.
"""

# ruff: noqa: T201, S603, S607 # a CLI that prints and runs git, docker, taskset and uv

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
PORT = int(os.environ.get("LOADTEST_AB_PORT", "18100"))
LOAD_WARNING = 1.5
STACK_TIMEOUT = 900  # seconds for build + migrations + healthy backend + seed
STEP_TIMEOUT = 600  # seconds per load step before the generator counts as hung


def parse_cpu_list(text: str) -> list[int]:
    """Expand a kernel CPU list such as ``0-3,5,8-9``."""
    cpus: list[int] = []
    for part in text.strip().split(","):
        if not part:
            continue
        low, _, high = part.partition("-")
        cpus.extend(range(int(low), int(high or low) + 1))
    return cpus


def allowed_cpus() -> list[int]:
    """The CPUs this process may run on."""
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("Cpus_allowed_list:"):
            return parse_cpu_list(line.split(":", 1)[1])
    return sorted(os.sched_getaffinity(0))


def siblings(cpu: int) -> list[int]:
    """The hyperthreads sharing ``cpu``'s physical core (just ``cpu`` if unknown)."""
    path = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
    return parse_cpu_list(path.read_text()) if path.exists() else [cpu]


def split_cpus(allowed: list[int]) -> tuple[int, list[int], list[int]]:
    """Pick (backend CPU, generator CPUs, database/cache CPUs) from the allowed set.

    Whole cores, whose hyperthreads are all allowed, come first: the backend and each
    generator process take one thread of such a core and leave its sibling idle.
    """
    cores: dict[tuple[int, ...], list[int]] = {}
    for cpu in allowed:
        cores.setdefault(tuple(siblings(cpu)), []).append(cpu)
    whole = [cpus for key, cpus in cores.items() if set(key) <= set(allowed)]
    partial = [cpus for key, cpus in cores.items() if not set(key) <= set(allowed)]
    ordered = whole + partial
    if len(ordered) < 2:
        msg = f"Need CPUs on at least two cores, got {allowed}."
        raise SystemExit(msg)
    backend = ordered[0][0]
    generator = [cpus[0] for cpus in ordered[1:4]]
    used = set(ordered[0]) | {cpu for cpus in ordered[1:4] for cpu in siblings(cpus[0])}
    rest = [cpu for cpu in allowed if cpu not in used] or [cpu for cpu in allowed if cpu != backend]
    return backend, generator, rest


class Stack:
    """The prod-limited stack of one ref, built from its own temporary worktree."""

    def __init__(self, label: str, ref: str, workdir: Path, override: Path) -> None:
        self.label = label
        self.ref = ref
        self.project = f"tmp-6ss-ab-{label.lower()}"
        self.container = f"{self.project}-backend-1"
        self.tree = workdir / f"tree-{label.lower()}"
        self.workdir = workdir
        self.compose = [
            "docker",
            "compose",
            "-p",
            self.project,
            "--profile",
            "db-seed",
            "-f",
            "compose.yml",
            "-f",
            "compose.prod.yml",
            "-f",
            "backend/loadtest/compose.yml",
            "-f",
            str(override),
        ]

    def checkout(self) -> None:
        """Add the detached worktree and drop in this checkout's load-test files."""
        subprocess.run(["git", "worktree", "add", "--detach", str(self.tree), self.ref], cwd=REPO, check=True)
        shutil.rmtree(self.tree / "backend" / "loadtest", ignore_errors=True)
        shutil.copytree(
            BACKEND / "loadtest", self.tree / "backend" / "loadtest", ignore=shutil.ignore_patterns("__pycache__")
        )

    def run(self, *args: str, timeout: float) -> bool:
        """Run one compose command in the ref's worktree; False on failure or timeout."""
        log = self.workdir / f"{self.project}.log"
        env = {**os.environ, "LOADTEST_PORT": str(PORT)}
        with log.open("a") as out:
            try:
                result = subprocess.run(  # fixed argv
                    [*self.compose, *args],
                    cwd=self.tree,
                    env=env,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return False
        return result.returncode == 0

    def up(self) -> bool:
        """Start a fresh stack (new database) and seed it."""
        deadline = time.monotonic() + STACK_TIMEOUT
        return self.run("up", "-d", "--build", "--wait", "backend", timeout=STACK_TIMEOUT) and self.run(
            "run", "--rm", "--build", "database-seed", timeout=max(1, deadline - time.monotonic())
        )

    def down(self, *, images: bool = False) -> None:
        """Remove the stack and its volume (and its images, at the end)."""
        self.run("down", "-v", *(["--rmi", "local"] if images else []), timeout=300)

    def remove(self) -> None:
        """Remove the temporary worktree."""
        subprocess.run(["git", "worktree", "remove", "--force", str(self.tree)], cwd=REPO, check=False)


def load_average() -> float:
    """The one-minute load average, after printing `uptime` for the record."""
    print(
        f"  uptime: {subprocess.run(['uptime'], capture_output=True, text=True, check=False).stdout.strip()}",
        flush=True,
    )
    return os.getloadavg()[0]


def run_generator(stack: Stack, cpus: list[int], rooms: str, extra: list[str], out: Path) -> list[dict] | None:
    """Run this checkout's load generator against a stack; the step results, or None if it failed."""
    steps = len(rooms.split(","))
    cmd = [
        "taskset",
        "-c",
        ",".join(map(str, cpus)),
        "uv",
        "run",
        "python",
        "-m",
        "loadtest.run",
        "--url",
        f"ws://127.0.0.1:{PORT}",
        "--container",
        stack.container,
        "--rooms",
        rooms,
        "--workers",
        str(len(cpus)),
        "--keep-going",
        "--json",
        str(out),
        *extra,
    ]
    try:
        subprocess.run(cmd, cwd=BACKEND, timeout=steps * STEP_TIMEOUT, check=False)
    except subprocess.TimeoutExpired:
        print(f"  {stack.label}: the load generator hung", flush=True)
        return None
    return json.loads(out.read_text()) if out.exists() else None


def failed(step: dict) -> bool:
    """A step errored when the server reported errors or nothing was delivered."""
    return sum(step["errors"].values()) > 0 or not step["deliveries_per_s"]


def cpu_per_kdeliveries(step: dict) -> float:
    """Backend CPU % spent per 1,000 deliveries/s."""
    return step["cpu_pct"] / (step["deliveries_per_s"] / 1000) if step["deliveries_per_s"] else math.nan


METRICS = {
    "p95 ms": lambda s: s["p95_ms"],
    "CPU %": lambda s: s["cpu_pct"],
    "deliveries/s": lambda s: s["deliveries_per_s"],
    "CPU %/1k del/s": cpu_per_kdeliveries,
}


def summarise(results: dict[str, dict[int, list[dict]]], labels: dict[str, str]) -> None:
    """Print median and range per step, ref and metric, then the ratio B/A of the medians."""
    print(f"\nA = {labels['A']}, B = {labels['B']}\n")
    print("| Rooms | Metric | A median | A range | B median | B range | B/A |")
    print("|---:|---|---:|---:|---:|---:|---:|")
    for rooms in sorted(results["A"].keys() | results["B"].keys()):
        for name, get in METRICS.items():
            cells = []
            medians = []
            for label in "AB":
                values = [get(s) for s in results[label].get(rooms, [])]
                values = [v for v in values if not math.isnan(v)]
                median = statistics.median(values) if values else math.nan
                medians.append(median)
                spread = f"{min(values):,.1f}-{max(values):,.1f}" if values else "-"
                cells += [f"{median:,.1f}", spread]
            ratio = medians[1] / medians[0] if medians[0] else math.nan
            print(f"| {rooms} | {name} | {' | '.join(cells)} | {ratio:.2f} |")


def parse_args(argv: list[str] | None) -> tuple[argparse.Namespace, list[str]]:
    """Parse the command line; unknown flags pass through to loadtest.run."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ref_a")
    parser.add_argument("ref_b")
    parser.add_argument("--runs", type=int, default=3, help="runs per ref, alternating A, B, A, B...")
    parser.add_argument("--rooms", default="40,50,60", help="comma-separated room counts per run")
    return parser.parse_known_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the alternating comparison and print the summary."""
    args, extra = parse_args(argv)
    backend_cpu, generator_cpus, rest = split_cpus(allowed_cpus())
    print(f"backend on CPU {backend_cpu}, load generator on {generator_cpus}, database and cache on {rest}", flush=True)
    workdir = Path(tempfile.mkdtemp(prefix="6ss-loadtest-ab-"))
    override = workdir / "cpuset.yml"
    rest_list = ",".join(map(str, rest))
    override.write_text(
        f'services:\n  backend:\n    cpuset: "{backend_cpu}"\n'
        f'  database:\n    cpuset: "{rest_list}"\n  cache:\n    cpuset: "{rest_list}"\n'
    )
    stacks = {"A": Stack("A", args.ref_a, workdir, override), "B": Stack("B", args.ref_b, workdir, override)}
    results: dict[str, dict[int, list[dict]]] = {"A": defaultdict(list), "B": defaultdict(list)}
    status = 0
    try:
        for stack in stacks.values():
            stack.checkout()
        for run in range(1, args.runs + 1):
            for stack in stacks.values():
                print(f"\nrun {run}/{args.runs}, {stack.label} ({stack.ref})", flush=True)
                if load_average() > LOAD_WARNING:
                    print(f"  warning: host load is above {LOAD_WARNING}; expect noisier numbers", flush=True)
                if not stack.up():
                    print(
                        f"  {stack.label} ({stack.ref}) failed to start; see {workdir / stack.project}.log", flush=True
                    )
                    stack.down()
                    return 1
                steps = run_generator(stack, generator_cpus, args.rooms, extra, workdir / f"{stack.label}-{run}.json")
                stack.down()
                if not steps:
                    print(f"  {stack.label}: the run produced no results", flush=True)
                    return 1
                for step in steps:
                    results[stack.label][step["rooms"]].append(step)
                    if failed(step):
                        print(
                            f"  {stack.label}: run {run} errored at {step['rooms']} rooms: {step['errors']}", flush=True
                        )
                        status = 1
        summarise(results, {label: stack.ref for label, stack in stacks.items()})
    finally:
        for stack in stacks.values():
            stack.down(images=True)
            stack.remove()
    shutil.rmtree(workdir, ignore_errors=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
