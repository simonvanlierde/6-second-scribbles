"""Ramp WebSocket load against the room server until broadcast latency degrades.

Each simulated room has one host and N-1 guests speaking the real room protocol:
every player scribbles on the shared lobby drawpad (``draw_stroke_partial`` 20
times a second, as the browser sends them), and every room regularly plays a one-round game
(server-dealt cards, a drawing, ready, guesses, scoring, restart). The
measured latency is send-to-receive time of a stroke fragment as seen by the
other players in the room, which is the hot broadcast path.

Run it through ``just loadtest`` (starts the prod-limited stack) or point it at a
running backend::

    uv run python -m loadtest.run --url ws://127.0.0.1:8000 --smoke
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import json
import math
import multiprocessing
import random
import re
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

# SharedDrawpad.vue sends buffered points every 50 ms.
SEND_HZ = 20
STROKE_FRAGMENTS = 10  # half a second of continuous drawing per stroke
POINTS_PER_FRAGMENT = 6
PAUSE_SECONDS = (0.5, 1.5)  # gap between strokes, uniform
# The largest drawing the frontend sends: encodeDrawing (frontend/src/lib/
# drawingImage.ts) shrinks every drawing to at most 56 KiB of data URL.
FAKE_DRAWING = "data:image/webp;base64,"
FAKE_DRAWING += "A" * (56 * 1024 - len(FAKE_DRAWING))
SERVER_ERROR_TYPES = {
    "protocol_error",
    "permission_error",
    "player_ready_error",
    "submit_guess_error",
    "join_error",
    "kick_error",
}
MAX_ROOMS = 500  # settings.max_total_rooms


# The server bounds game timers (15-180 s) and stroke widths (at most 64), so the
# generator must send values a real client could; tests/unit/test_loadtest_messages.py
# validates these messages against the server's protocol models.
MIN_ROUND_SECONDS = 15
SEND_TIME_PREFIX = "t"


def stroke_fragment(player_id: str, points: list[int], sent: float, *, start: bool) -> dict[str, object]:
    """A lobby stroke fragment whose `color` carries the monotonic send time.

    The server relays the fragment unchanged, so the receiver reads the time back
    from `color`; `width` stays a real pen width the server accepts.
    """
    return {
        "type": "draw_stroke_partial",
        "playerId": player_id,
        "stroke": {"color": f"{SEND_TIME_PREFIX}{sent:.6f}", "width": 4, "points": points},
        "strokeStart": start,
    }


def sent_at(stroke: dict[str, object]) -> float:
    """The monotonic send time a fragment from `stroke_fragment` carries."""
    return float(str(stroke["color"]).removeprefix(SEND_TIME_PREFIX))


def start_game_message(draw_seconds: float) -> dict[str, object]:
    """A one-round start_game within the server's timer bounds.

    Players press ready before the timer runs out, so a long limit does not slow
    the rounds down.
    """
    return {
        "type": "start_game",
        "rounds": 1,
        "difficulty": "easy",
        "drawingTimeLimit": max(MIN_ROUND_SECONDS, math.ceil(draw_seconds)),
        "guessingTimeLimit": MIN_ROUND_SECONDS,
    }


LOBBY, FINAL = "lobby", "final"
# The room phase each server event moves a client into.
PHASE_AFTER = {
    "start_game": "starting",
    "start_round": "drawing",
    "start_guessing": "guessing",
    "round_complete": "results",
    "game_complete": FINAL,
    "restart_game": LOBBY,
}


@dataclass
class Config:
    """Workload shape, shared by every worker process."""

    url: str
    players: int
    lobby_seconds: float
    draw_seconds: float
    end_at: float  # time.monotonic() deadline; CLOCK_MONOTONIC is shared across processes
    window: tuple[float, float]  # latency samples count only inside this monotonic window


@dataclass
class Stats:
    """Counters from one worker, merged across workers for a step."""

    latencies_ms: list[float] = field(default_factory=list)
    rounds_scored: int = 0
    errors: Counter[str] = field(default_factory=Counter)
    cpu_share: float = 0.0

    def merge(self, other: Stats) -> None:
        """Fold another worker's stats into this one."""
        self.latencies_ms.extend(other.latencies_ms)
        self.rounds_scored += other.rounds_scored
        self.errors.update(other.errors)
        self.cpu_share = max(self.cpu_share, other.cpu_share)


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile (q in 0..100); NaN for no samples."""
    if not values:
        return math.nan
    ordered = sorted(values)
    rank = max(1, math.ceil(q / 100 * len(ordered)))
    return ordered[rank - 1]


def parse_mem_mib(usage: str) -> float:
    """Parse the used half of `docker stats` MemUsage ("123.4MiB / 1GiB") into MiB."""
    used = usage.split("/", 1)[0].strip()
    match = re.fullmatch(r"([\d.]+)\s*(B|KiB|MiB|GiB)", used)
    if match is None:
        msg = f"Unrecognised memory value: {usage!r}"
        raise ValueError(msg)
    return float(match[1]) * {"B": 2**-20, "KiB": 2**-10, "MiB": 1, "GiB": 2**10}[match[2]]


def is_knee(p95_ms: float, errors: int, limit_ms: float) -> bool:
    """A step has degraded when p95 crosses the limit, any error occurs, or nothing arrived."""
    return errors > 0 or math.isnan(p95_ms) or p95_ms > limit_ms


class Player:
    """One simulated browser tab in a room."""

    def __init__(self, cfg: Config, stats: Stats, room: str, seat: int, host_joined: asyncio.Event) -> None:
        self.cfg = cfg
        self.stats = stats
        self.room = room
        self.seat = seat
        self.player_id = f"lt-{room}-{seat}"
        self.host_joined = host_joined
        self.phase = LOBBY
        self.ws: ClientConnection | None = None
        self.leaving = False
        self.background: set[asyncio.Task[None]] = set()

    @property
    def is_host(self) -> bool:
        """Seat 0 joins first and so owns the room."""
        return self.seat == 0

    async def send(self, payload: dict[str, object]) -> None:
        """Send one client event as JSON."""
        if self.ws is not None:
            await self.ws.send(json.dumps(payload))

    async def run(self) -> None:
        """Connect, join, play until the deadline, then leave."""
        if not self.is_host:
            await self.host_joined.wait()
        # Each room poses as its own client IP: the prod config trusts the rightmost
        # X-Forwarded-For hop (set by Caddy), and room creation is limited per IP.
        forwarded_for = f"10.{int(self.room[:2]) % 256}.{int(self.room[2:]) // 256}.{int(self.room[2:]) % 256}"
        try:
            async with connect(
                f"{self.cfg.url}/ws/{self.room}",
                additional_headers={"X-Forwarded-For": forwarded_for},
                max_size=None,
                open_timeout=30,
            ) as ws:
                self.ws = ws
                await self.send({"type": "join", "playerId": self.player_id, "name": f"Bot {self.seat}"})
                tasks = [asyncio.create_task(self.draw_loop())]
                if self.is_host:
                    tasks.append(asyncio.create_task(self.host_loop()))
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self.receive_loop(), timeout=max(0.0, self.cfg.end_at - time.monotonic()))
                for task in tasks:
                    task.cancel()
                await self.leave()
        except ConnectionClosed:
            if not self.leaving:
                self.stats.errors["disconnect"] += 1
        except OSError, InvalidHandshake, TimeoutError:
            self.stats.errors["connect_failed"] += 1
        finally:
            self.host_joined.set()  # never leave guests waiting on a host that failed

    async def leave(self) -> None:
        """Hand the room to the next step clean.

        The host resets it to the lobby (a start_game may still be in flight), guests
        leave, then the host leaves last so the room empties without scheduling a
        host transfer.
        """
        self.leaving = True
        with contextlib.suppress(ConnectionClosed):
            if self.is_host:
                await self.send({"type": "restart_game"})
            await asyncio.sleep(2.0 if self.is_host else 0.5)
            await self.send({"type": "leave"})

    def record_relay(self, msg: dict, now: float) -> None:
        """Time the other players' stroke fragments in a relayed message."""
        window_start, window_end = self.cfg.window
        if not window_start <= now <= window_end:
            return
        for fragment in msg["fragments"]:
            if fragment.get("playerId") != self.player_id:
                self.stats.latencies_ms.append((now - sent_at(fragment["stroke"])) * 1000)

    async def receive_loop(self) -> None:
        """Track the room phase, react to the game flow, and time stroke relays."""
        assert self.ws is not None  # noqa: S101 # set by run() before this starts
        async for raw in self.ws:
            now = time.monotonic()
            msg = json.loads(raw)
            kind = msg.get("type")
            self.phase = PHASE_AFTER.get(kind, self.phase)
            match kind:
                case "draw_stroke_batch":
                    self.record_relay(msg, now)
                case "player_joined" if msg.get("playerId") == self.player_id:
                    if self.is_host and not msg.get("isHost"):
                        self.stats.errors["not_host"] += 1
                    self.host_joined.set()
                case "start_round":
                    task = asyncio.create_task(self.finish_drawing())
                    self.background.add(task)
                    task.add_done_callback(self.background.discard)
                case "start_guessing":
                    await self.submit_guess(msg.get("guessTargets", {}).get(self.player_id))
                case "round_complete" if self.is_host:
                    self.stats.rounds_scored += 1
                case _ if kind in SERVER_ERROR_TYPES:
                    self.stats.errors[f"{kind}:{msg.get('error')}"] += 1

    async def finish_drawing(self) -> None:
        """Send the round's drawing and mark ready; in-game drawing itself stays local."""
        await asyncio.sleep(self.cfg.draw_seconds * random.uniform(0.5, 1.0))  # noqa: S311
        with contextlib.suppress(ConnectionClosed):
            await self.send({"type": "draw_stroke", "playerId": self.player_id, "drawing": FAKE_DRAWING})
            await self.send({"type": "player_ready", "playerId": self.player_id})

    async def submit_guess(self, target: str | None) -> None:
        """Guess the drawing the server assigned to this player, if any."""
        if target:
            await self.send(
                {
                    "type": "submit_guess",
                    "playerId": self.player_id,
                    "targetPlayerId": target,
                    "guesses": ["cat", "house", "tree"],
                }
            )

    async def draw_loop(self) -> None:
        """Scribble on the shared lobby drawpad while the room is in the lobby."""
        rng = random.Random()  # noqa: S311 # load shape, not security
        await asyncio.sleep(rng.uniform(0, 1))
        while True:
            if self.phase != LOBBY:
                await asyncio.sleep(0.2)
                continue
            # Pad coordinates, 0-10000 across and down the pad; a step of 60 is about
            # 5 px on an 800 px wide pad.
            x, y = rng.randint(0, 10_000), rng.randint(0, 10_000)
            for frame in range(STROKE_FRAGMENTS):
                points = []
                for _ in range(POINTS_PER_FRAGMENT):
                    x = min(10_000, max(0, x + rng.randint(-60, 60)))
                    y = min(10_000, max(0, y + rng.randint(-60, 60)))
                    points += [x, y]
                await self.send(stroke_fragment(self.player_id, points, time.monotonic(), start=frame == 0))
                await asyncio.sleep(1 / SEND_HZ)
            await asyncio.sleep(rng.uniform(*PAUSE_SECONDS))

    async def host_loop(self) -> None:
        """Start a one-round game after each lobby spell and restart after the results."""
        while True:
            # Jitter the lobby time so rooms' games do not line up.
            await asyncio.sleep(random.uniform(0.5, 1.5) * self.cfg.lobby_seconds)  # noqa: S311
            if self.phase == LOBBY:
                await self.send(start_game_message(self.cfg.draw_seconds))
            # The server ignores start_game until a second player has joined, so the
            # phase may stay in the lobby; otherwise wait for the final results.
            await asyncio.sleep(0.5)
            while self.phase not in {LOBBY, FINAL}:  # noqa: ASYNC110 # polls a field the receive loop sets
                await asyncio.sleep(0.5)
            if self.phase == FINAL:
                await asyncio.sleep(2)  # a look at the results
                await self.send({"type": "restart_game"})


async def run_rooms(cfg: Config, rooms: list[str], stats: Stats) -> None:
    """Connect every player of the given rooms and play until the deadline."""
    players = []
    for room in rooms:
        host_joined = asyncio.Event()
        players.extend(Player(cfg, stats, room, seat, host_joined) for seat in range(cfg.players))
    await asyncio.gather(*(player.run() for player in players))


def run_worker(cfg: Config, rooms: list[str]) -> Stats:
    """Process entry point: run a share of the rooms on its own event loop."""
    stats = Stats()
    cpu_start = time.process_time()
    asyncio.run(run_rooms(cfg, rooms, stats))
    window = cfg.window[1] - cfg.window[0]
    stats.cpu_share = (time.process_time() - cpu_start) / window if window > 0 else 0.0
    return stats


def sample_container(container: str) -> tuple[float, float] | None:
    """Return (CPU %, memory MiB) for a container, or None if docker stats fails."""
    result = subprocess.run(  # noqa: S603 # fixed argv, container name from our own CLI
        ["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}\t{{.MemUsage}}", container],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    cpu, mem = result.stdout.strip().split("\t")
    return float(cpu.rstrip("%")), parse_mem_mib(mem)


@dataclass
class StepResult:
    """One row of the capacity table."""

    rooms: int
    players: int
    p50_ms: float
    p95_ms: float
    deliveries_per_s: float
    cpu_pct: float
    mem_mib: float
    errors: Counter[str]
    rounds_scored: int
    generator_cpu_pct: float

    def as_json(self) -> dict[str, object]:
        """The fields as plain JSON values."""
        # asdict alone would rebuild the Counter from (key, value) pairs and count the pairs.
        return {**dataclasses.asdict(self), "errors": dict(self.errors)}

    @property
    def connections(self) -> int:
        """Open sockets at this step."""
        return self.rooms * self.players

    def row(self) -> str:
        """Format as a Markdown table row matching TABLE_HEADER."""
        errors = ", ".join(f"{k}={v}" for k, v in sorted(self.errors.items())) or "0"
        return (
            f"| {self.rooms} | {self.players} | {self.connections} | {self.p50_ms:.0f} | {self.p95_ms:.0f}"
            f" | {self.deliveries_per_s:,.0f} | {self.cpu_pct:.0f}% | {self.mem_mib:.0f} MiB | {errors}"
            f" | {self.rounds_scored} | {self.generator_cpu_pct:.0f}% |"
        )


TABLE_HEADER = (
    "| Rooms | Players/room | Connections | p50 ms | p95 ms | Deliveries/s | Backend CPU | Backend mem"
    " | Errors | Rounds scored | Load-gen CPU |\n"
    "|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|"
)


def run_step(args: argparse.Namespace, rooms: int) -> StepResult:
    """Run one load level and collect its stats."""
    workers = max(1, min(args.workers, rooms))
    settle = 3 + rooms * args.players / 200  # time to open every socket before measuring
    start = time.monotonic()
    window = (start + settle, start + settle + args.duration)
    cfg = Config(
        url=args.url.rstrip("/"),
        players=args.players,
        lobby_seconds=args.lobby_seconds,
        draw_seconds=args.draw_seconds,
        end_at=window[1],
        window=window,
    )
    # The same codes every step: rooms are reused instead of piling up toward MAX_ROOMS.
    codes = [f"{args.prefix:02d}{i:04d}" for i in range(rooms)]
    shares = [codes[i::workers] for i in range(workers)]
    samples: list[tuple[float, float]] = []
    with multiprocessing.get_context("spawn").Pool(workers) as pool:
        pending = pool.starmap_async(run_worker, [(cfg, share) for share in shares])
        while not pending.ready():
            if args.container and window[0] <= time.monotonic() <= window[1]:
                sample = sample_container(args.container)
                if sample:
                    samples.append(sample)
            pending.wait(timeout=1)
        results = pending.get()
    # Outlast the server's 5 s host-transfer delay, so a transfer left over from a
    # slow leave cannot promote a guest of the next step.
    time.sleep(6)
    stats = Stats()
    for result in results:
        stats.merge(result)
    return StepResult(
        rooms=rooms,
        players=args.players,
        p50_ms=percentile(stats.latencies_ms, 50),
        p95_ms=percentile(stats.latencies_ms, 95),
        deliveries_per_s=len(stats.latencies_ms) / args.duration,
        cpu_pct=sum(s[0] for s in samples) / len(samples) if samples else math.nan,
        mem_mib=max((s[1] for s in samples), default=math.nan),
        errors=stats.errors,
        rounds_scored=stats.rounds_scored,
        generator_cpu_pct=stats.cpu_share * 100,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="ws://127.0.0.1:18000", help="backend base URL (ws://host:port)")
    parser.add_argument("--rooms", default="5,10,20,30,40,60,80,100", help="comma-separated room counts to step")
    parser.add_argument("--players", type=int, default=6, help="players per room (server max is 10)")
    parser.add_argument("--duration", type=float, default=40, help="measured seconds per step")
    parser.add_argument("--lobby-seconds", type=float, default=15, help="lobby doodling between games")
    parser.add_argument("--draw-seconds", type=float, default=3, help="in-game drawing time per round")
    parser.add_argument("--p95-limit", type=float, default=250, help="p95 latency (ms) that marks the knee")
    parser.add_argument("--workers", type=int, default=4, help="load-generator processes")
    parser.add_argument("--container", help="backend container to sample with docker stats")
    parser.add_argument("--prefix", type=int, default=10, help="two-digit room code prefix")
    parser.add_argument("--smoke", action="store_true", help="a few seconds at tiny load; fails on any problem")
    parser.add_argument("--keep-going", action="store_true", help="run every step, also past the knee")
    parser.add_argument("--json", metavar="PATH", help="also write the step results to PATH as JSON")
    args = parser.parse_args(argv)
    if args.smoke:
        # The host starts the game 4-12 s in and the window opens at about 3 s, so every
        # window holds some lobby drawing and still sees the round scored.
        args.rooms, args.players, args.duration, args.lobby_seconds, args.draw_seconds = "2", 3, 20, 8, 1
    return args


def main(argv: list[str] | None = None) -> int:
    """Step through the room counts and stop at the first degraded step."""
    args = parse_args(argv)
    steps = [int(n) for n in args.rooms.split(",")]
    if max(steps) > MAX_ROOMS:
        sys.exit(f"The server caps rooms at {MAX_ROOMS}.")
    print(TABLE_HEADER, flush=True)  # noqa: T201
    knee: StepResult | None = None
    last: StepResult | None = None
    results: list[StepResult] = []
    for rooms in steps:
        last = run_step(args, rooms)
        results.append(last)
        if args.json:
            # Rewritten after every step, so a run cut short still leaves its finished steps.
            with open(args.json, "w", encoding="utf-8") as out:  # noqa: PTH123
                json.dump([r.as_json() for r in results], out)
        print(last.row(), flush=True)  # noqa: T201
        if last.generator_cpu_pct > 80:
            print("  warning: a load-generator process was near a full core; raise --workers", flush=True)  # noqa: T201
        if is_knee(last.p95_ms, sum(last.errors.values()), args.p95_limit) and knee is None:
            knee = last
            if not args.keep_going:
                break
    if args.smoke:
        ok = last is not None and knee is None and last.rounds_scored > 0
        print("smoke: ok" if ok else "smoke: FAILED (errors, no deliveries, or no round scored)")  # noqa: T201
        return 0 if ok else 1
    if knee:
        print(f"knee: {knee.rooms} rooms x {knee.players} players ({knee.connections} connections)")  # noqa: T201
    else:
        print("no knee within the configured steps; extend --rooms")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
