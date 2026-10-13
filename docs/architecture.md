# Architecture

6 Second Scribbles keeps three parts in one repo: a Vue 3 single-page frontend, a
FastAPI backend, and a set of committed contracts that keep the two sides in sync.
This page is the overview. The [frontend](../frontend/README.md) and
[backend](../backend/README.md) READMEs cover each side in more detail.

## Runtime Topology

In production, the only way in from outside is a Cloudflare tunnel. Caddy serves
the built SPA and passes `/api` and `/ws` on to the backend over the internal
Docker network, so the backend is never published directly. Redis holds the
short-lived room and session state. PostgreSQL holds the content that must last:
users and category data. Database migrations run to completion before the backend
starts.

```mermaid
flowchart TD
    Browser["Player browser<br/>(Vue 3 SPA)"]
    Tunnel["Cloudflare Tunnel"]
    Frontend["Frontend container<br/>Caddy + built SPA<br/>proxies /api and /ws"]
    Backend["Backend container<br/>FastAPI<br/>HTTP /api + WS /ws/{room_id}"]
    Redis[("Redis<br/>room state, sessions,<br/>rate limits")]
    Postgres[("PostgreSQL<br/>users, categories")]
    Migrations["Alembic migrations<br/>(gate backend startup)"]

    Browser <--> Tunnel
    Tunnel <--> Frontend
    Frontend <-->|internal network| Backend
    Backend --> Redis
    Backend --> Postgres
    Migrations -.->|completes first| Backend
```

The overrides in [`compose.prod.yml`](../compose.prod.yml) pin the resource limits,
bind the frontend to loopback, and pin `cloudflared` by image digest. The comments
in that file give the reason for each one.

## Contract-First Boundary

The backend owns the wire format. Its route and schema definitions and the room
protocol are exported into `contracts/` as an OpenAPI document and JSON Schema
files. The frontend generates its TypeScript and Zod types from those committed
files, so it never guesses at the shape of a message. CI checks that the backend
still reproduces the committed contracts. If the two sides drift apart, the build
fails before the change reaches the running app.

[ADR 0001](adr/0001-committed-generated-contracts.md) records why we chose this
and what else we considered.

```mermaid
flowchart LR
    subgraph Backend
        Protocol["Room protocol +<br/>route schemas"]
    end
    Contracts["contracts/<br/>openapi.json<br/>room-events.json<br/>jsonschema/"]
    subgraph Frontend
        Generated["src/generated/<br/>api.ts + protocol.ts"]
    end

    Protocol -->|generate-contracts| Contracts
    Contracts -->|contracts:generate| Generated
    Contracts -.->|check-contracts in CI| Contracts
```

## Game Loop

A room is a small state machine. The backend drives it and pushes each change to
every client over WebSockets. Players move through the phases below. After the
last round the room lands on final results, and a restart returns it to the lobby.

```mermaid
stateDiagram-v2
    [*] --> lobby
    lobby --> drawing: start_game
    drawing --> guessing: start_guessing
    guessing --> round_results: round_complete
    round_results --> drawing: next round
    round_results --> final_results: last round
    final_results --> lobby: restart_game
```

[`GamePhase`](../backend/app/core/types.py) defines the phase values. The client
and server message types that drive the transitions live in
[`app/rooms/protocol.py`](../backend/app/rooms/protocol.py).
