# Backend

The backend is a FastAPI app. It serves the HTTP API under `/api` and the WebSocket
game protocol under `/ws/{room_id}`. PostgreSQL stores users and category content;
Redis holds runtime state, sessions, and room coordination.

## Main Modules

- `app/auth/`: guest sessions
- `app/users/`: current-user profile
- `app/categories/`: category lookup, locale handling, and guess scoring support
- `app/rooms/`: room lifecycle, gameplay state, and WebSocket orchestration
- `app/system/`: health and service metadata endpoints
- `app/core/`: configuration, logging, database, Redis, and shared infrastructure

## Local Setup

From the `backend/` directory:

```bash
just install
cp .env.example .env.dev
just dev          # http://localhost:8000
```

Other commands:

```bash
just test         # pytest suite
just check        # formatting, linting, and static type checks
just format
just migrate
just migrate-new "describe-change"
just seed
just generate-contracts
```

## Data Model Notes

Each category and prompt is stored once as base content, with its translations for
every locale in a JSONB `translations` column, so one copy of the game logic checks
guesses and shows prompts in every language. The tables are `categories`, `prompts`
and `category_prompts`.
