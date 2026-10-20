---
status: accepted
date: 2026-06-29
---

# Committed, generated contracts as the frontend/backend source of truth

## Context and Problem Statement

The backend (FastAPI) and the frontend (Vue/TypeScript) are separate apps in one
repo. They exchange HTTP requests and a fairly large set of WebSocket messages,
so both sides must agree on the exact shape of every payload. How do we keep the
two sets of types in sync without writing every definition twice by hand, and
without the copies drifting apart unnoticed?

## Considered Options

- **Hand-written TypeScript types** on the frontend that mirror the Python models.
- **Runtime code generation:** fetch the OpenAPI schema from a running backend
  and generate the types during each frontend build.
- **Committed, generated contracts:** export OpenAPI and JSON Schema from the
  backend into a tracked `contracts/` directory, generate the frontend types from
  those files, and check in CI that regenerating gives the same files.

## Decision Outcome

Chosen option: **committed, generated contracts**. The backend is the single
source of truth. `just generate-contracts` writes `contracts/openapi.json`,
`contracts/room-events.json`, and one JSON Schema file per event. The frontend
generates its `src/generated/` types from them. The `contracts` CI job runs
`pnpm run contracts:check`, which fails the build if the backend no longer
reproduces the committed files. `just check-contracts` runs the same check locally.

### Consequences

- Good, because a backend change to the wire format shows up as a diff in
  `contracts/`. Reviewers see the API change in the PR that causes it.
- Good, because CI catches drift between the two sides, before the running app does.
- Good, because the frontend can build without a running backend. The contracts
  are just files in the repo.
- Bad, because contributors must remember to regenerate after a protocol change.
  The CI check is the safety net: forgetting gives a failed build, not a bug that
  hides until later.
- Neutral, because the generated files add noise to some diffs. They are marked
  as generated, and nobody edits them by hand.
