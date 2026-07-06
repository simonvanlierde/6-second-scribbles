# Architecture

6 Second Scribbles is a monorepo with a Vue 3 single-page frontend, a FastAPI
backend, and a set of committed contracts that keep the two sides in sync. This
page gives a high-level map; the [frontend](../frontend/README.md) and
[backend](../backend/README.md) READMEs cover each side in more detail.

## Runtime Topology

In production the only external ingress is a Cloudflare tunnel. Caddy serves the
built SPA and reverse-proxies `/api` and `/ws` to the backend over the internal
Docker network, so the backend is never published directly. Redis holds
ephemeral room and session state; PostgreSQL holds durable content (users and
category data). Database migrations run to completion before the backend starts.

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

The [`compose.prod.yml`](../compose.prod.yml) overrides pin resource limits, bind
the frontend to loopback, and pin `cloudflared` by image digest. See its inline
comments for the reasoning behind each choice.

## Contract-First Boundary

The backend owns the wire format. Its route and schema definitions and the room
protocol are exported into `contracts/` as an OpenAPI document and JSON Schema
files. The frontend generates its TypeScript and Zod types from those committed
artifacts — it never guesses at the shape of a message. CI checks that the
committed contracts are reproducible from the backend, so a drift between the two
sides fails the build instead of reaching runtime.

The rationale and alternatives are recorded in
[ADR 0001](adr/0001-committed-generated-contracts.md).

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

A room is a small state machine driven by the backend and pushed to every client
over WebSockets. Players move through the phases below; after the last round the
room lands on final results, and a restart returns it to the lobby.

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

The phase values are defined in
[`GamePhase`](../backend/app/core/types.py); the client and server message types
that drive the transitions live in
[`app/rooms/protocol.py`](../backend/app/rooms/protocol.py).
