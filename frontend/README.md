# Frontend

The frontend is a Vue 3 single-page app for creating rooms, joining games, drawing, guessing, and viewing round results in real time.

## Responsibilities

- Lobby and gameplay UI
- Drawing pad and guessing interactions
- Real-time room updates over WebSockets
- Auth and session state in Pinia
- Client code generated from tracked backend contracts
- Unit and end-to-end browser tests

## Main Areas

- `src/views/`: route-level screens
- `src/components/`: reusable UI building blocks
- `src/composables/`: connection, canvas, timer, and room lifecycle logic
- `src/stores/`: auth, game, and drawing state
- `src/shared/`: shared types and small domain helpers
- `src/generated/`: generated API and protocol types

## Routes

- `/`: home and room entry flow
- `/rooms/:roomCode`: live room experience

The room route renders different states for lobby, drawing, guessing, round results, final results, and spectators based on the current server state.

## Local Setup

From the `frontend/` directory:

1. Install dependencies:

   ```bash
   pnpm install
   ```

2. Optional: create a local env file if you want to point the app at a custom backend:

   ```bash
   cp .env.example .env.local
   ```

3. Start the dev server:

   ```bash
   pnpm run dev
   ```

By default the app runs on `http://localhost:3001` in the Docker-backed dev setup used by the repo.

## Common Commands

```bash
pnpm run dev
pnpm run build
pnpm run lint
pnpm run type-check
pnpm run test:unit
pnpm run test:e2e
pnpm run contracts:generate
```

There is also a local `justfile` if you prefer `just` wrappers.

## Generated Code

The frontend consumes committed contract artifacts from the repo and generates:

- `src/generated/api.ts` from `contracts/openapi.json`
- `src/generated/protocol.ts` from the WebSocket schemas in `contracts/`

Regenerate them after contract changes with `pnpm run contracts:generate`.

## Testing

- Vitest covers component, store, composable, and utility tests
- Playwright covers browser-level flows such as navigation, lobby behavior, and waiting-room interactions
