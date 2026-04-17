# 6 Second Scribbles

6 Second Scribbles is a real-time multiplayer drawing and guessing game for short, room-based rounds. One player draws through a rapid list of prompts, everyone else tries to identify what was drawn, and the room cycles through lobby, round, and results states over WebSockets.

This repository contains the full stack application:

- `frontend/`: Vue 3 app built with Vite, Pinia, and Vue Router
- `backend/`: FastAPI application with PostgreSQL and Redis
- `contracts/`: committed API and WebSocket contract artifacts shared between both sides

## What The Project Includes

- Public room flow with real-time multiplayer state
- Guest and registered-user auth flows
- Category and prompt data with locale-aware translations
- Generated client/server contracts to keep frontend and backend aligned
- Unit, integration, and end-to-end test coverage

## Tech Stack

- Frontend: Vue 3, TypeScript, Pinia, Vite, vue-i18n
- Backend: FastAPI, SQLAlchemy, PostgreSQL, Redis
- Tooling: pnpm, uv, just, Docker Compose, Playwright, Vitest, pytest

## Getting Started

### Prerequisites

- Node.js 24+
- Python 3.14+
- `pnpm`
- `uv`
- `just`
- Docker and Docker Compose

### Local Development

1. Install dependencies:

   ```bash
   just install
   ```

2. Create local environment files:

   ```bash
   cp backend/.env.example backend/.env.dev
   cp frontend/.env.example frontend/.env.local
   ```

3. Start the full development stack:

   ```bash
   just dev
   ```

This starts Docker services plus the frontend and backend dev servers. If you only want the containerized stack, use `just up`.

### Useful Commands

```bash
just dev
just up
just down
just test
just check
just format
just generate-contracts
```

## Project Docs

- [Frontend](frontend/README.md)
- [Backend](backend/README.md)
- [Contracts](contracts/README.md)

## Notes On Scope

This is still an early-stage project. The codebase favors simple, understandable implementations over preserving every old behavior or optimization.

## Attribution

This multiplayer implementation is inspired by:

1. *Six Second Scribbles*, created by Hazel Reynolds and published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles)
2. The solo web version by Oliver Culley de Lange on [GitHub](https://github.com/OliverCulleyDeLange/6ss)

## License

The code in this repository is released under the MIT License.

The original *Six Second Scribbles* game concept, brand, and card content remain the property of their respective owners.
