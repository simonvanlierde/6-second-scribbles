# Capacity

This page says how many rooms and players one backend container holds under the
production limits in [`compose.prod.yml`](../compose.prod.yml) (1.0 CPU, 1 GiB
memory, one uvicorn worker), and where it starts to slow down.

## Result

With every player scribbling at once, one backend holds about **200 rooms of 6
players (1,200 WebSocket connections)** with the p95 broadcast latency under
250 ms. (p95 means 95% of messages arrive at least this fast.) In the run below,
p95 stays near 52 ms up to 160 rooms; 50 ms of that is the server's stroke tick,
which holds each room's doodle fragments and sends them out together. At 240 rooms
one run reached 445 ms, and at 280 rooms the next one 127 ms, so the knee sits
somewhere from 200 to 280 rooms. Backend CPU was at 82% at 280 rooms, and memory
stayed under 280 MiB of the 1 GiB limit.

Measured on 2026-10-21. Rows up to 140 rooms come from commit `b9f6804`, and the
rest from `30537fb`, which raised the backend's open file limit: with Docker's
default soft limit of 1024 descriptors, one per WebSocket, the server turned away
connections from about 1,000 players on, with CPU to spare.

| Rooms | Players/room | Connections | p50 | p95 | Deliveries/s | Backend CPU | Backend memory | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 40 | 6 | 240 | 46 ms | 52 ms | 4,773 | 22% | 116 MiB | 0 |
| 60 | 6 | 360 | 46 ms | 52 ms | 7,288 | 28% | 130 MiB | 0 |
| 80 | 6 | 480 | 45 ms | 52 ms | 9,136 | 37% | 143 MiB | 0 |
| 100 | 6 | 600 | 45 ms | 52 ms | 11,680 | 44% | 154 MiB | 0 |
| 120 | 6 | 720 | 44 ms | 53 ms | 13,088 | 53% | 170 MiB | 0 |
| 140 | 6 | 840 | 44 ms | 59 ms | 15,090 | 55% | 181 MiB | 0 |
| 160 | 6 | 960 | 44 ms | 53 ms | 16,900 | 58% | 184 MiB | 0 |
| 200 | 6 | 1,200 | 51 ms | 144 ms | 19,555 | 74% | 221 MiB | 0 |
| 240 | 6 | 1,440 | 52 ms | 445 ms | 20,979 | 77% | 259 MiB | 0 |
| 280 | 6 | 1,680 | 51 ms | 127 ms | 26,678 | 82% | 270 MiB | 0 |

Each row is one run, so expect noise near the knee; `just loadtest-ab` (below)
repeats runs when two versions need comparing.

**Earlier versions.** v0.3.0, driven the way its browser client sent strokes (one
message per screen frame, points as pixel objects), reached p95 674 ms at 60 rooms
on the same host and day, at 90% CPU. On 2026-10-12, commit `85ddbea` held about
80 rooms. Four changes moved the knee: the browser sends every 50 ms instead of
every frame, the server batches each room's fragments per 50 ms tick, points travel
as flat integers, and per-message deflate is off.

The runs used one host: `AMD Ryzen 7 H 255 w/ Radeon 780M Graphics`, 8 cores and
16 threads (from `/proc/cpuinfo`). Backend CPU is the `docker stats` CPU, averaged
over the step, where 100% is the whole 1.0 CPU limit. Memory is the peak.
Deliveries/s counts the stroke fragments that reached another player. The load
generator ran on the same host, outside the limited container, and used at most
59% of one core per process.

**Bottleneck:** the event loop's CPU. Each room sends every player one batch per
50 ms tick, however many fragments arrived in it, so the work grows with rooms ×
players, plus the parsing of each incoming fragment.

## Workload

The test script ([`backend/loadtest/run.py`](../backend/loadtest/run.py)) speaks
the real room protocol, with one WebSocket per player:

- The host opens `/ws/{room}` and joins. The guests join after the host.
- In the lobby every player draws on the shared drawpad: strokes of 10
  `draw_stroke_partial` fragments at 20 per second (six points each, as the
  browser sends them every 50 ms), with 0.5 to 1.5 s between strokes. That is
  about 7 messages per second per player, so this is a busy lobby, not an
  average one. The server sends each room's fragments out together every
  50 ms, as one `draw_stroke_batch`.
- After 7.5 to 22.5 s in the lobby, the host starts a one-round game. The server
  deals the cards. Each player sends a 56 KiB `draw_stroke`, the largest
  drawing the frontend sends, and `player_ready`. (The tables above used a
  20 KB drawing.) Then each player submits guesses for its assigned drawing.
  The host restarts the game after the final results.
- Latency is the time from a player sending a stroke fragment to another
  player in the same room receiving the relay. Errors count failed connects,
  unexpected disconnects, and any error event from the server.

Each step runs for 40 s after all sockets are open. The ramp stops at the
first step whose p95 passes 250 ms or that has any error. The test script talks
to the backend directly. The frontend's Caddy proxy, which has its own 0.5 CPU
limit, is not part of the measurement.

## Running it

```bash
just loadtest                      # build the prod stack, seed it, ramp, tear down
just loadtest --smoke              # 2 rooms x 3 players for a few seconds; fails on any problem
just loadtest --rooms 60,70,80 --players 8
```

`just loadtest` runs the stack as the Compose project `tmp-6ss-load` with the
prod build and limits, plus
[`backend/loadtest/compose.yml`](../backend/loadtest/compose.yml), which swaps
in throwaway credentials and publishes the backend on `127.0.0.1:18000`
(`LOADTEST_PORT` changes it). It removes the stack, its volume, and its images
when it finishes. To aim the test at a backend you already run, use
`just backend/loadtest --url ws://127.0.0.1:8000 --smoke`.

### Comparing two commits

```bash
just loadtest-ab 85ddbea main                          # 3 runs each, one 20 s step at 40 rooms: about 5 minutes
just loadtest-ab main HEAD --runs 5 --rooms 60,70,80   # other flags, such as --duration, pass through to run.py
```

This builds each commit's prod stack from a temporary worktree outside the
checkout, but always drives it with the load generator from your
checkout, so an old server meets today's workload. Runs alternate A, B, A, B, so
a change in host load during the comparison hits both commits alike. Both stacks
are built and seeded once and stay up for every run, on `LOADTEST_AB_PORT` and the
port after it (18100 and 18101 by default). The backend container is pinned to one CPU (still
capped at 1.0 CPU), the load generator to up to three other cores, and Postgres
and Redis to what is left. On a CPU with hyperthreads, the backend's and the
generator's twin threads stay idle. The script prints the host load before each
run and warns above 1.5.

The summary gives, per step, the median and range of p95, backend CPU,
deliveries/s, and backend CPU per 1,000 deliveries/s, then B/A of the medians.
The last one is the fairest speed measure below the knee, where both commits
deliver everything sent. The command fails if any run had errors or delivered
nothing, or if a commit's stack does not start.

### Benchmarks on every PR

CodSpeed runs `backend/tests/benchmarks` on every PR and on main
(`.github/workflows/benchmarks.yml`) and reports on the PR when one gets slower:
validating a stroke fragment, encoding a `draw_stroke_batch`, fanning it out to six
connections, and storing a new stroke on a full doodle; scoring a guesser's submission;
and saving and loading a mid-round room snapshot for Redis. It counts CPU instructions,
so the result does not depend on how busy the runner is. It measures only code in
this process, not uvicorn or websockets, so dependency bumps and releases still
need `just loadtest-ab`. To try the benchmarks locally:
`cd backend && uv run pytest tests/benchmarks --codspeed` (wall time, not instructions).

Outside prod, the backend ignores `X-Forwarded-For` by default, so every test room comes
from the same client. That client may hold at most 5 open rooms and create 10
rooms a minute, so keep `--rooms` at 5 or below there.
