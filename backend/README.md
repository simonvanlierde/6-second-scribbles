# Backend

The backend is a FastAPI app. It handles sign-in, category data, rooms from creation to close, scoring, and the real-time game protocol.

## Responsibilities

- HTTP API under `/api`
- WebSocket game transport under `/ws/{room_id}`
- Users and category content, stored in PostgreSQL
- Runtime state, sessions, and room coordination, held in Redis
- Database migrations and seed tooling
- Contract export for the frontend

## Main Modules

- `app/auth/`: guest and account auth flows
- `app/users/`: current-user profile and preferences
- `app/categories/`: category lookup, locale handling, and guess scoring support
- `app/rooms/`: room lifecycle, gameplay state, and WebSocket orchestration
- `app/system/`: health and service metadata endpoints
- `app/core/`: configuration, logging, database, Redis, and shared infrastructure

## Local Setup

From the `backend/` directory:

1. Install dependencies:

   ```bash
   just install
   ```

2. Create a local env file:

   ```bash
   cp .env.example .env.dev
   ```

3. Run the development server:

   ```bash
   just dev
   ```

The server runs on `http://localhost:8000`.

## Common Commands

```bash
just dev
just test
just check
just format
just migrate
just migrate-new "describe-change"
just seed
just translate-seed
just seed-auto
just generate-contracts
```

## Data Model Notes

Each category is stored once as base content, with a separate translation for each locale. That way the game can check guesses and show prompts in different languages with one copy of the game logic.

The main content tables are:

- `categories`
- `category_translations`
- `category_items`
- `category_item_translations`

## Seed Data

Local seed data includes a demo account:

- username: `demo_host`
- password: `demo-password`

## Testing

- `just test` runs the backend pytest suite
- `just check` runs formatting, linting, and static type checks

Tests cover HTTP routes, room lifecycle behavior, scoring, and WebSocket flows.
