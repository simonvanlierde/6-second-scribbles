# Architecture

A Vue 3 single-page frontend, a FastAPI backend, and committed contracts that keep
the two in sync. The [frontend](../frontend/README.md) and
[backend](../backend/README.md) READMEs cover each side.

## Runtime topology

The live demo runs on my own server as the Compose stack in
[`compose.prod.yml`](../compose.prod.yml), started with `just up-prod`. The only
way in from outside is a Cloudflare Tunnel (`cloudflared`, in the Compose `tunnel`
profile). Caddy serves the built SPA and passes `/api` and `/ws` to the backend
over the internal Docker network. No port is open to the internet. The backend
starts only after the database migrations finish.

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

The comments in `compose.prod.yml` explain each resource limit, the loopback bind,
and the digest pin on `cloudflared`.

## Contract-first boundary

The backend owns the wire format and exports it into `contracts/`. The frontend
generates its types from those files, and CI fails if the backend no longer
reproduces them. [ADR 0001](adr/0001-committed-generated-contracts.md) has the
reasons and the alternatives.

```mermaid
flowchart LR
    subgraph Backend
        Protocol["Room protocol +<br/>route schemas"]
    end
    Contracts["contracts/<br/>openapi.json<br/>jsonschema/"]
    subgraph Frontend
        Generated["src/generated/<br/>api.ts + protocol.ts"]
    end

    Protocol -->|generate-contracts| Contracts
    Contracts -->|contracts:generate| Generated
    Contracts -.->|check-contracts in CI| Contracts
```

## Game loop

A room is a small state machine. The backend drives it and pushes each change to
every client over WebSockets.

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

[`GamePhase`](../backend/app/core/types.py) defines the phases. The client and
server messages that drive the transitions are in
[`app/rooms/protocol.py`](../backend/app/rooms/protocol.py).
