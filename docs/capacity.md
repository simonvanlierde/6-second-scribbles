# Capacity

This page says how many rooms and players one backend container holds under the
production limits in [`compose.prod.yml`](../compose.prod.yml) (1.0 CPU, 1 GiB
memory, one uvicorn worker), and where it starts to slow down.

## Result

With every player scribbling at once, one backend holds up to about **80 rooms of
6 players (480 WebSocket connections)** with the p95 broadcast latency under
250 ms. (p95 means 95% of messages arrive at least this fast.) At 90 rooms, p95
reaches 264 ms. CPU is the limit: from 70 rooms on, the single worker sits near its
1.0 CPU cap, while memory stays under 270 MiB of the 1 GiB limit.

Commit `85ddbea` made each broadcast serialize to JSON once instead of once per
recipient. That moved the knee, where latency starts to climb fast, from about 70
to about 80 rooms. The gain is small, because the server still sends once per
recipient.

### After: one serialization per broadcast

Measured on 2026-10-12 against commit `85ddbea`. The 70 to 90 room rows come from
a second run. The first run gave p95 192 ms at 70 rooms, 126 ms at 80 and 601 ms
at 100. So expect about ±50% noise between runs near the knee.

| Rooms | Players/room | Connections | p50 | p95 | Deliveries/s | Backend CPU | Backend memory | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 6 | 30 | 1 ms | 2 ms | 1,833 | 16% | 101 MiB | 0 |
| 10 | 6 | 60 | 1 ms | 2 ms | 3,671 | 25% | 112 MiB | 0 |
| 20 | 6 | 120 | 1 ms | 2 ms | 7,769 | 40% | 131 MiB | 0 |
| 40 | 6 | 240 | 1 ms | 11 ms | 15,171 | 65% | 170 MiB | 0 |
| 50 | 6 | 300 | 2 ms | 13 ms | 18,898 | 75% | 189 MiB | 0 |
| 60 | 6 | 360 | 3 ms | 28 ms | 22,245 | 83% | 212 MiB | 0 |
| 70 | 6 | 420 | 14 ms | 55 ms | 25,859 | 88% | 220 MiB | 0 |
| 80 | 6 | 480 | 33 ms | 155 ms | 29,313 | 93% | 243 MiB | 0 |
| 90 | 6 | 540 | 47 ms | 264 ms | 31,530 | 92% | 262 MiB | 0 |

### Before: one serialization per recipient

Measured on 2026-10-12 against commit `71d868c`.

| Rooms | Players/room | Connections | p50 | p95 | Deliveries/s | Backend CPU | Backend memory | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 6 | 30 | 1 ms | 2 ms | 1,863 | 16% | 98 MiB | 0 |
| 10 | 6 | 60 | 1 ms | 2 ms | 3,960 | 29% | 111 MiB | 0 |
| 20 | 6 | 120 | 1 ms | 2 ms | 7,887 | 46% | 130 MiB | 0 |
| 40 | 6 | 240 | 2 ms | 6 ms | 15,376 | 71% | 167 MiB | 0 |
| 50 | 6 | 300 | 3 ms | 33 ms | 18,570 | 83% | 180 MiB | 0 |
| 60 | 6 | 360 | 15 ms | 63 ms | 22,524 | 91% | 208 MiB | 0 |
| 70 | 6 | 420 | 46 ms | 198 ms | 25,313 | 91% | 225 MiB | 0 |
| 80 | 6 | 480 | 95 ms | 354 ms | 29,480 | 95% | 250 MiB | 0 |

Both runs used one host: `AMD Ryzen 7 H 255 w/ Radeon 780M Graphics`, 8 cores and
16 threads (from `/proc/cpuinfo`). Backend CPU is the `docker stats` CPU, averaged
over the step, where 100% is the whole 1.0 CPU limit. Memory is the peak.
Deliveries/s counts the stroke fragments that reached another player. The load
generator ran on the same host, outside the limited container, and used at most
34% of one core per process.

**Bottleneck:** the event loop's CPU. Each relayed stroke is sent once per player
in the room, so the work grows with rooms × players². Past the knee, either send
fewer messages (batch the stroke fragments per frame on the server) or give the
worker more CPU.

## Workload

The test script ([`backend/loadtest/run.py`](../backend/loadtest/run.py)) speaks
the real room protocol, with one WebSocket per player:

- The host opens `/ws/{room}` and joins. The guests join after the host.
- In the lobby every player draws on the shared drawpad: strokes of 10
  `draw_stroke_partial` fragments at 20 per second (six points each, as the
  browser sends them every 50 ms), with 0.5 to 1.5 s between strokes. That is
  about 7 messages per second per player, so this is a busy lobby, not an
  average one. `--send-hz 60` replays the older client, which sent one fragment
  per browser frame. The server sends each room's fragments out together every
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
just loadtest-ab c7bbe1c HEAD --a-args=--point-objects  # flags for one side: A predates pad coordinates
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

Outside prod, the backend ignores `X-Forwarded-For` by default, so every test room comes
from the same client. That client may hold at most 5 open rooms and create 10
rooms a minute, so keep `--rooms` at 5 or below there.
