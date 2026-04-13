---
# spell-checker: words Culley, Lange
---
# 6 Second Scribbles

Real-time multiplayer drawing and guessing, built for quick room-based play.

## What It Is

Each round, the game assigns a category and a short list of prompts to every player. Players draw as many prompts as they can, then another player tries to guess them. The backend now treats categories and items as canonical multilingual content, so prompts can be localized per player instead of forcing one room-wide language.

## Current Product Shape

- Real-time multiplayer rooms over WebSockets
- Same-origin HTTP API under `/api` and WebSockets under `/ws`
- Multilingual room support with per-player locale preference
- Canonical category/item model with localized labels and aliases
- Guest play plus lightweight first-party accounts
- Owner-only private categories for registered users
- Host defaults plus room-level overrides for private categories
- Vue 3 frontend with Pinia state and generated websocket contracts
- FastAPI backend with PostgreSQL, Redis, and Alembic

## Quick Start

### Prerequisites

- Node.js 24+
- Python 3.12+
- Docker
- `just`

### Install

```bash
just install
```

### Run locally

```bash
just dev
```

That runs the frontend and backend on your machine while Docker provides local Postgres and Redis.

### Run the full Docker dev stack

```bash
just up-dev
```

Open `http://localhost:3001`.

## Common Commands

```bash
just dev
just up-dev
just up-prod
just build
just check
just format
```

Direct test commands:

```bash
uv --project backend run pytest
pnpm --dir frontend run test:unit
pnpm --dir frontend exec vue-tsc --build --force
```

## Architecture

### Frontend

- Vue 3 + Vite
- Pinia for shared app/game/auth/category state
- Vue Router with:
  - `/`
  - `/profile`
  - `/rooms/:roomCode`
- Generated protocol types from the websocket contract

Main frontend areas:

- [frontend/src/views/HomeView.vue](/Users/simon/code/personal/6-second-scribbles/frontend/src/views/HomeView.vue)
- [frontend/src/views/RoomView.vue](/Users/simon/code/personal/6-second-scribbles/frontend/src/views/RoomView.vue)
- [frontend/src/views/LobbyView.vue](/Users/simon/code/personal/6-second-scribbles/frontend/src/views/LobbyView.vue)
- [frontend/src/views/ProfileView.vue](/Users/simon/code/personal/6-second-scribbles/frontend/src/views/ProfileView.vue)

### Backend

- FastAPI for HTTP and websocket endpoints
- PostgreSQL for durable data
- Redis for room/session runtime state and rate-limit helpers
- Alembic migrations for schema changes

Main backend boundaries:

- `/api/auth` for guest/register/login/logout
- `/api/me` for profile/preferences
- `/api/categories` for system and owner-visible category data
- `/api/rooms` for room HTTP helpers
- `/ws/{roomCode}` for live room traffic

## Categories And Locales

The backend now models categories as language-neutral concepts:

- `categories`
- `category_translations`
- `category_items`
- `category_item_translations`

That lets the game:

- localize prompts per player
- validate guesses against the guesser’s locale first
- fall back to room default locale, category default locale, then English when needed

Private categories:

- are available only to registered users
- are owner-only for now
- can be marked `enabled_by_default` for hosted rooms
- can be overridden per room by the host
- are soft-deleted instead of hard-deleted
- are eligible for cleanup if they remain unused for a long time

## Accounts

The app currently uses lightweight first-party auth:

- guest session bootstrap
- register with username + password
- login/logout with server-side sessions in Redis
- per-user preferred locale

Custom categories are intentionally limited to registered users so guests cannot fill the database with throwaway private content.

## Docker And Deployment

The production stack uses a dedicated frontend container:

- `compose.override.yml` runs the frontend in Vite dev mode with hot reload
- `compose.prod.yml` builds the frontend into a Caddy image
- Caddy serves the SPA and proxies `/api` and `/ws` to the backend

### Production-style local run

```bash
just up-prod
```

### Cloudflare Tunnel

The intended tunnel flow is:

- Cloudflare Tunnel
- `cloudflared`
- `frontend` container
- internal backend service

That means the public hostname points at the frontend container, and Caddy forwards backend traffic internally on the Docker network.

## Seeded Demo Account

Fresh local seeds now include one registered demo account plus a couple of owner-only private categories:

- username: `demo_host`
- password: `demo-password`

That makes it easier to test profile flows, host defaults, and room-level custom category overrides without creating content manually every time.

## Notes For Contributors

- Prefer simplicity over backward compatibility when the code gets meaningfully cleaner
- Keep API HTTP routes under `/api` and websocket traffic under `/ws`
- Run related tests after changes
- If you touch both frontend and backend, run both suites before finishing

More backend detail lives in [backend/README.md](/Users/simon/code/personal/6-second-scribbles/backend/README.md).

This project is a real-time, multiplayer web version inspired by two wonderful creations:

1. **The original physical game:** *Six Second Scribbles*, created by **Hazel Reynolds** and published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles).
1. **The original solo web version:** by **Oliver Culley de Lange**, which you can find [on GitHub](https://github.com/OliverCulleyDeLange/6ss).

This implementation rebuilds the game from the ground up as a multiplayer experience using Vue 3, Pinia, and FastAPI.

## 🤝 Contributing

Got ideas? Contributions are definitely welcome. Feel free to open an issue or send a PR. Some things on my mind:

- More card decks
- Smarter fuzzy-matching for guesses
- Animations, sound effects, or a spectator mode
- Game history and player stats

## 📝 License

The code for *this* multiplayer implementation is released under the **MIT License**.

The *Six Second Scribbles* game concept, brand, and original card content remain the property of their respective owners.
