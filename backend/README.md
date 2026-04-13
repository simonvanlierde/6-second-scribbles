---
# spell-checker: ignore elefant, htmlcov
---
# Backend

FastAPI backend for Six Second Scribbles.

## What Lives Here

- HTTP API under `/api`
- WebSocket room transport under `/ws`
- PostgreSQL-backed user and category data
- Redis-backed session, room-runtime, and rate-limit helpers
- Alembic migrations
- Pytest coverage for HTTP, websocket, and room lifecycle behavior

## Current Backend Shape

### Core tech

- FastAPI
- SQLAlchemy async ORM
- PostgreSQL
- Redis
- Alembic
- RapidFuzz

### Main app areas

- `app/auth/`
- `app/users/`
- `app/categories/`
- `app/rooms/`
- `app/scoring/`
- `app/core/`

## Local Development

The main project workflow from the repository root is:

```bash
just dev
```

If you want to run backend tasks directly:

```bash
uv --project backend run alembic upgrade head
uv --project backend run python backend/scripts/seed_data.py
uv --project backend run pytest
```

To auto-fill missing seed translations (offline models, larger disk usage is expected):

```bash
just backend/translate-seed
just backend/seed-auto
```

Notes:

- Translation source locale defaults to `en`.
- Target locales default to `es fr`.
- First run downloads Argos models and can take time + a few GB.
- Existing non-empty translations are preserved unless you pass `--overwrite-existing`.

## Seed Translation via Docker (Local Model Storage)

For local hosting, the `database-seed` service mounts an Argos model cache from your machine:

- Host path default: `./backend/.argos-models`
- Container path: `/home/appuser/.local/share/argos-translate`

You can override the host cache path with `ARGOS_MODELS_DIR`.

Example:

```bash
ARGOS_MODELS_DIR="$HOME/.local/share/argos-translate" docker compose --profile database-seed run --rm database-seed python scripts/auto_translate_seed_data.py --target-locales es fr
```

Then seed with the translated data:

```bash
docker compose --profile database-seed run --rm database-seed
```

Useful translation flags:

- `--dry-run` to preview without writing `scripts/seed_data.yaml`
- `--overwrite-existing` to regenerate existing non-empty translations
- `--source-locale en` and `--target-locales es fr` to control language direction

Interactive docs are available at `http://localhost:8000/docs` when the app is running.

## Data Model

### Users

The app now uses lightweight first-party auth:

- guest bootstrap
- register/login/logout
- Redis-backed server-side sessions
- per-user preferred locale

### Categories

Categories are modeled as canonical multilingual content:

- `categories`
- `category_translations`
- `category_items`
- `category_item_translations`

This lets the backend:

- localize prompts per player
- validate guesses in the guesser’s locale first
- fall back through room default locale, category default locale, then English
- score by canonical item IDs instead of localized strings

## Main Endpoints

### Auth

```text
POST /api/auth/guest
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/me
PATCH /api/me/preferences
```

### Categories

```text
GET    /api/categories
POST   /api/score/guesses
```

### Rooms and system

```text
GET  /api/health
GET  /api/stats
GET  /api/rooms/{room_id}/status
POST /api/rooms/{room_id}/category-selection
WS   /ws/{room_id}
```

## Seeded Demo Data

Fresh local seeds include:

- system categories from [seed_data.json](/Users/simon/code/personal/6-second-scribbles/backend/scripts/seed_data.json)
- one registered demo account
- two owner-only private categories for that account

Demo credentials:

- username: `demo_host`
- password: `demo-password`

## Testing

Run the backend suite:

```bash
uv --project backend run pytest
```

Useful targeted runs:

```bash
uv --project backend run pytest backend/tests/test_main.py -x --tb=short
uv --project backend run pytest backend/tests/test_services.py -x --tb=short
uv --project backend run pytest backend/tests/test_game_room.py -x --tb=short
```

Coverage:

```bash
uv --project backend run pytest --cov=backend/app --cov-report=html
```

## Notes

- Keep HTTP routes under `/api` and WebSockets under `/ws`
- Prefer canonical IDs over localized strings in runtime room state
- Keep Redis for ephemeral runtime concerns, not canonical content storage
- Prefer simplifying refactors over preserving early-dev legacy behavior
