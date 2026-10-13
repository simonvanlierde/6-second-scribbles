# 6 Second Scribbles

[![CI](https://github.com/simonvanlierde/6-second-scribbles/actions/workflows/ci.yml/badge.svg)](https://github.com/simonvanlierde/6-second-scribbles/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/simonvanlierde/6-second-scribbles/branch/main/graph/badge.svg)](https://codecov.io/gh/simonvanlierde/6-second-scribbles)
[![6ss.duinlab.nl](https://img.shields.io/website?url=https%3A%2F%2F6ss.duinlab.nl&up_message=online&down_message=offline)](https://6ss.duinlab.nl)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

6 Second Scribbles is a multiplayer drawing and guessing game that runs in real time. One player races through a list of prompts while everyone else guesses what's being drawn. Each room moves from the lobby to the rounds to the results, and the players stay in sync over WebSockets.

You can play the live demo at [6ss.duinlab.nl](https://6ss.duinlab.nl).

| The drawer's view | What the guessers see |
| --- | --- |
| ![Drawer working through a themed prompt list](docs/screenshots/desktop-drawing.png) | ![Guesser racing to name each doodle](docs/screenshots/desktop-guessing.png) |

## Stack

- **Frontend:** Vue 3, TypeScript, Pinia, Vite, vue-i18n
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Tooling:** pnpm, uv, just, Docker Compose, Vitest, Playwright, pytest

Everything lives in one repo with three parts: `frontend/`, `backend/`, and `contracts/`. The contracts are the committed OpenAPI and WebSocket schemas that both sides share. [docs/architecture.md](docs/architecture.md) shows how the pieces fit together, and [docs/adr/](docs/adr/) records the design decisions.

## Status

### Working

- Real-time multiplayer rooms over WebSockets
- Full game loop: lobby → drawing → guessing → results
- Guest and registered-user accounts
- Locale-aware prompt categories and guess matching
- Generated client/server contracts
- Unit, integration, and end-to-end tests

### Todo

- Full mobile support (the layout is desktop-first for now)
- Better handling of players who disconnect mid-game

## Accessibility

CI checks accessibility in three ways:

- **Static a11y linting.** Biome's accessibility rules are on (`linter.rules.a11y: "on"` in `biome.json`), and `pnpm --dir frontend run lint` runs them. They catch markup problems such as missing labels, invalid ARIA, and click handlers on elements that are not interactive.
- **axe scans.** Playwright with [`@axe-core/playwright`](https://github.com/dequelabs/axe-core-npm) scans Home, the Settings panel, and the `/__ds` component-library page against the WCAG 2.1 A/AA rule tags, in both the light and the dark theme. These scans need only the frontend, not the backend, and run as the `a11y` CI job. Run them locally with `just test-a11y`.
- **Accessibility-tree assertions.** The wider Playwright e2e suite finds elements by ARIA role and accessible name (`getByRole`, including `getByRole("status")` for notifications). So those flows pass only when the roles and labels are really there. They run as the `e2e` CI job against Postgres and Redis service containers. Run them locally with `just test-e2e`, which needs the backend stack.

These tools check specific WCAG A/AA **rules**. A passing axe run means it found no violations of those rules. It is not a full manual audit, and it does **not** certify WCAG AA conformance.

## Running locally

Requires Node 26+, Python 3.14+, `pnpm`, `uv`, `just`, and Docker.

```bash
just install                                   # install dependencies
cp backend/.env.example backend/.env.dev
cp frontend/.env.example frontend/.env.local
just dev                                        # Docker services + dev servers
```

`just up` runs the whole stack in containers. `just test`, `just check`, and `just format` run the tests, the linters, and the formatters. The [frontend](frontend/README.md), [backend](backend/README.md), and [contracts](contracts/README.md) docs have more detail. If you'd like to contribute, read [CONTRIBUTING.md](CONTRIBUTING.md).

## Deployment

The live demo at [6ss.duinlab.nl](https://6ss.duinlab.nl) runs on my own server,
as the Docker Compose stack in [`compose.prod.yml`](compose.prod.yml). I start it
on the host with `just up-prod`. Caddy serves the built SPA and passes `/api` and
`/ws` on to the backend. PostgreSQL and Redis stay on the internal Docker network.
The only way in from outside is a Cloudflare Tunnel (`cloudflared`, in the Compose
`tunnel` profile), so nothing is published straight to the internet.
[docs/architecture.md](docs/architecture.md) shows the full layout.
[docs/capacity.md](docs/capacity.md) says how many rooms one backend holds
under the production limits, and `just loadtest` measures it.

## Attribution

Inspired by *Six Second Scribbles* by Hazel Reynolds, published by [Gamely Games](https://gamelygames.com/products/six-second-scribbles), and the solo web version by [Oliver Culley de Lange](https://github.com/OliverCulleyDeLange/6ss).

## License

Code is released under the [MIT License](LICENSE). The original *Six Second Scribbles* game concept, brand, and card content remain the property of their respective owners.
