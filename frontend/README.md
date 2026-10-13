# Frontend

The frontend is a Vue 3 single-page app. Players use it to create rooms, join games, draw, guess, and see the round results in real time.

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

## Dependency notes

`@vueuse/motion` (registered in `src/main.ts`) and `html-to-image` are installed,
but no screen uses them yet.

## Routes

- `/`: home and room entry flow
- `/rooms/:roomCode`: live room experience

The room route shows a different screen for the lobby, drawing, guessing, round results, final results, and spectators. The server's current state decides which one.

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

In the repo's Docker-backed dev setup, the app runs on `http://localhost:3001` by default.

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

If you prefer `just`, a local `justfile` wraps these.

## Generated Code

The frontend generates two files from the committed contracts:

- `src/generated/api.ts` from `contracts/openapi.json`
- `src/generated/protocol.ts` from the WebSocket schemas in `contracts/`

Regenerate them after contract changes with `pnpm run contracts:generate`.

## Testing

- Vitest covers component, store, composable, and utility tests
- Playwright covers browser-level flows such as navigation, lobby behavior, and waiting-room interactions
