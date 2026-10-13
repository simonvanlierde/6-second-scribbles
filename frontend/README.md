# Frontend

The frontend is a Vue 3 single-page app. Players use it to create rooms, join games,
draw, guess, and see the round results in real time.

## Main Areas

- `src/views/`: route-level screens
- `src/components/`: reusable UI building blocks
- `src/composables/`: connection, canvas, timer, and room lifecycle logic
- `src/stores/`: auth, game, and drawing state (Pinia)
- `src/shared/`: shared types and small domain helpers
- `src/generated/`: API and protocol types generated from [`contracts/`](../contracts/README.md);
  regenerate with `pnpm run contracts:generate`

## Routes

- `/`: home and room entry flow
- `/rooms/:roomCode`: live room experience

The room route shows a different screen for the lobby, drawing, guessing, round
results, final results, and spectators. The server's current state decides which one.

## Dependency notes

`@vueuse/motion` (registered in `src/main.ts`) and `html-to-image` are installed,
but no screen uses them yet.

## Local Setup

From the `frontend/` directory:

```bash
pnpm install
cp .env.example .env.local   # optional: point the app at a custom backend
pnpm run dev
```

In the repo's Docker-backed dev setup, the app runs on `http://localhost:3001` by default.

Other commands (a local `justfile` wraps these):

```bash
pnpm run build
pnpm run lint
pnpm run type-check
pnpm run test:unit     # Vitest: components, stores, composables, utilities
pnpm run test:e2e      # Playwright: browser-level flows
pnpm run contracts:generate
```
