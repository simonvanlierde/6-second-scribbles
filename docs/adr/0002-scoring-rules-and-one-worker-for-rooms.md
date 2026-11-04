---
status: accepted
date: 2026-10-21
---

# Scoring rules, and rooms stay in one worker

## Context and Problem Statement

Two choices shape how a game behaves and how the backend runs. The game rules
were ruled on 2026-10-21. Where room state lives was settled in the same period
and checked again on 2026-11-03.

## Decision Outcome

Game rules (ruled 2026-10-21):

- A player who leaves keeps their score.
- A new game resets the players who are present to 0.
- The white pen stays.
- Guesses are scored in the same locale chain as the card.

Rooms stay in one worker. The backend runs `uvicorn` with `--workers 1`. If the
app ever runs more workers, Caddy must route each room to one worker.

Per-player state goes through three metadata methods, and the stored JSON is
unchanged. Because the stored shape did not change, a rollback stays possible.

### Consequences

- Good, because sharing room state through Redis would cost 20 or more hours,
  and the project judged that not worth it.
- Bad, because one worker is the ceiling for concurrent rooms until Caddy routes
  rooms to workers.
- Rolling back past #43 loses live rooms.
- A change to any of the four game rules needs a new record.
