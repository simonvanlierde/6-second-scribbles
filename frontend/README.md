# Frontend

Vue 3 frontend for Six Second Scribbles, built with Vite, Pinia, Vue Router, and vue-i18n.

## What Lives Here

- Home and room gameplay views
- Shared drawing, guessing, lobby, and results UI
- App state in Pinia stores
- Websocket and API client code generated from tracked contracts
- Unit tests with Vitest and end-to-end tests with Playwright

## Main Areas

- `src/views/` for the route-level screens
- `src/components/` for reusable UI pieces
- `src/composables/` for connection, drawing, timing, and notification logic
- `src/stores/` for auth, game, and drawing state
- `src/shared/` for room-code and game-phase utilities
- `src/generated/` for contract-derived TypeScript and Zod types

## Routes

- `/` for the home and room entry flow
- `/rooms/:roomCode` for the active room experience

The room view swaps between lobby, drawing, guessing, round results, final results, and spectator states based on live game state.

## Local Development

From the frontend directory:

```bash
pnpm install
pnpm run dev
pnpm run test:unit
pnpm run test:e2e
pnpm run lint
pnpm run type-check
pnpm run build
pnpm run contracts:generate
```

If you prefer the local `justfile`, the matching wrappers are available there too.

## Generated Code

The frontend keeps two generated files under `src/generated/`:

- `protocol.ts` from `contracts/jsonschema/` and `contracts/room-events.json`
- `api.ts` from `contracts/openapi.json`

Regenerate them with `pnpm run contracts:generate` after contract changes.

## Testing

- Vitest covers unit tests under `src/**/__tests__/`
- Playwright covers browser flows under `e2e/`
- `pnpm run type-check` runs Vue and TypeScript checks for the app

## Notes

- Keep UI state simple and predictable
- Prefer generated contract types over hand-written API shapes
- Match the backend contract before adding new client behavior
