# Capacity

How many rooms and players one backend container holds under the production
limits in [`compose.prod.yml`](../compose.prod.yml) (1.0 CPU, 1 GiB memory, one
uvicorn worker), and where it starts to degrade.

## Result

Up to about **70 rooms of 6 players (420 WebSocket connections)** with every
player scribbling at once, p95 broadcast latency stays under 250 ms. At 80
rooms p95 reaches 354 ms. The limit is CPU: the single worker sits at
its 1.0 CPU cap from 60 rooms on, while memory stays under 260 MiB of the
1 GiB limit.

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

Measured on 2026-10-12 against commit `71d868c` on an AMD Ryzen 7 H 255 w/
Radeon 780M Graphics host (8 cores, 16 threads, from `/proc/cpuinfo`). Backend
CPU is `docker stats` CPU averaged over the step, where 100% is the whole
1.0 CPU limit; memory is the peak. Deliveries/s counts stroke fragments that
reached another player. The load generator ran on the same host outside the
limited container, using at most 29% of one core per process.

**Bottleneck:** the event loop's CPU. Each relayed stroke is serialized and
sent once per player in the room, so work grows with rooms × players², and
latency climbs once the worker reaches its CPU cap. Serializing a broadcast
once instead of once per recipient is the first thing to try if this limit
matters.

## Workload

The harness ([`backend/loadtest/run.py`](../backend/loadtest/run.py)) speaks the
real room protocol, one WebSocket per player:

- The host opens `/ws/{room}` and joins; the guests join after it.
- In the lobby every player draws on the shared drawpad: strokes of 30
  `draw_stroke_partial` fragments at 60 per second (one per browser frame, two
  points each), with 0.5 to 1.5 s between strokes. That is about 20 messages
  per second per player, so this is a busy lobby, not an average one.
- After 7.5 to 22.5 s in the lobby the host starts a one-round game. The server
  deals the cards, each player sends a 20 KB PNG `draw_stroke` and
  `player_ready`, submits guesses for its assigned drawing, and the host
  restarts the game after the final results.
- Latency is the time from a player sending a stroke fragment to another
  player in the same room receiving the relay. Errors count failed connects,
  unexpected disconnects, and any error event from the server.

Each step runs for 40 s after all sockets are open. The ramp stops at the
first step whose p95 passes 250 ms or that has any error. The harness talks to
the backend directly; the frontend's Caddy proxy (its own 0.5 CPU limit) is not
part of the measurement.

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
when it finishes. To aim the harness at a backend you already run, use
`just backend/loadtest --url ws://127.0.0.1:8000 --smoke`; outside prod the
backend limits room creation to 10 per minute per client, so keep the room
count small there.
