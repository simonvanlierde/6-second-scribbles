# Backend

FastAPI backend for Six Second Scribbles.

## What Lives Here

- HTTP API under `/api`
- WebSocket room transport under `/ws`
- PostgreSQL-backed user, room, and category data
- Redis-backed sessions, room runtime, and rate-limit helpers
- Alembic migrations
- Pytest coverage for HTTP, websocket, and room lifecycle behavior

## Main Areas

- `app/auth/` for guest, register, login, and logout flows
- `app/users/` for profile and preference endpoints
- `app/categories/` for category data, locale availability, and guess scoring
- `app/rooms/` for room creation, room state, and websocket orchestration
- `app/system/` for health and stats endpoints
- `app/core/` for config, logging, database, and Redis wiring

## Local Development

From the backend directory:

```bash
just install
just dev
just test
just check
just format
just generate-contracts
```

Database and seed helpers:

```bash
just migrate
just migrate-new "your migration message"
just seed
just translate-seed
just seed-auto
```

If you prefer direct `uv` commands:

```bash
uv run alembic upgrade head
uv run python -m scripts.seed_data
uv run pytest
```

## API Surface

Common routes:

```text
POST /api/auth/guest
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/me
PATCH /api/me/preferences
GET  /api/categories
GET  /api/categories/locales
POST /api/score/guesses
GET  /api/rooms/random
POST /api/rooms/
GET  /api/rooms/{room_id}/status
POST /api/rooms/{room_id}/category-selection
GET  /api/health
GET  /api/stats
WS   /ws/{room_id}
```

## Data Model

Categories are modeled as canonical multilingual content:

- `categories`
- `category_translations`
- `category_items`
- `category_item_translations`

That lets the backend:

- localize prompts per player
- validate guesses against the guesser’s locale first
- fall back through room default locale, category default locale, then English
- score by canonical item IDs instead of localized strings

## Seeded Demo Data

Fresh local seeds include a demo account and owner-only private categories:

- username: `demo_host`
- password: `demo-password`

## Notes

- Keep HTTP routes under `/api` and WebSockets under `/ws`
- Prefer canonical IDs over localized strings in runtime room state
- Keep Redis for ephemeral runtime concerns, not canonical content storage
- Prefer simplifying refactors over preserving early-dev legacy behavior
