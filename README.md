# 6 Second Scribbles

6 Second Scribbles is a real-time, multiplayer drawing-and-guessing game. One player races through a list of prompts while everyone else guesses what's being drawn, and rooms move through lobby, round, and results states over WebSockets.

> **Work in progress** — the full game loop works and is covered by tests, but there's no hosted demo yet and the UI is mid-redesign.

## Stack

- **Frontend** — Vue 3, TypeScript, Pinia, Vite, vue-i18n
- **Backend** — FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Tooling** — pnpm, uv, just, Docker Compose, Vitest, Playwright, pytest

It's a monorepo: `frontend/`, `backend/`, and `contracts/` (committed OpenAPI and WebSocket schemas shared by both sides).

## Status

### Working

- Real-time multiplayer rooms over WebSockets
- Full game loop: lobby → drawing → guessing → results
- Guest and registered-user accounts
- Locale-aware prompt categories and guess matching
- Generated client/server contracts
- Unit, integration, and end-to-end tests

### Planned

- A public hosted demo (it currently runs locally only)
- Finishing the UI and design-system redesign (home and lobby done so far)

## Running locally

Requires Node 24+, Python 3.14+, `pnpm`, `uv`, `just`, and Docker.

```bash
just install                                   # install dependencies
cp backend/.env.example backend/.env.dev
cp frontend/.env.example frontend/.env.local
just dev                                        # Docker services + dev servers
```

`just up` runs the full containerized stack; `just test`, `just check`, and `just format` handle testing, linting, and formatting. See the [frontend](frontend/README.md), [backend](backend/README.md), and [contracts](contracts/README.md) docs for more.

## Attribution

Inspired by *Six Second Scribbles* by Hazel Reynolds, published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles), and the solo web version by [Oliver Culley de Lange](https://github.com/OliverCulleyDeLange/6ss).

## License

Code is released under the MIT License. The original *Six Second Scribbles* game concept, brand, and card content remain the property of their respective owners.
