---
status: accepted
date: 2026-06-29
---

# Committed, generated contracts as the frontend/backend source of truth

## Context and Problem Statement

The backend (FastAPI) and frontend (Vue/TypeScript) are separate applications in
one monorepo that exchange HTTP requests and a fairly large set of WebSocket
messages. Both sides need to agree on the exact shape of every payload. How do we
keep the two type systems in sync without hand-maintaining duplicate definitions
that silently drift apart?

## Considered Options

- **Hand-written TypeScript types** mirroring the Python models on the frontend.
- **Runtime code generation** — fetch the OpenAPI schema from a running backend
  and generate types on demand during frontend builds.
- **Committed, generated contracts** — export OpenAPI + JSON Schema from the
  backend into a tracked `contracts/` directory, generate the frontend types from
  those files, and verify reproducibility in CI.

## Decision Outcome

Chosen option: **committed, generated contracts**. The backend is the single
source of truth; `just generate-contracts` writes `contracts/openapi.json`,
`contracts/room-events.json`, and per-event JSON Schema files, and the frontend
generates its `src/generated/` types from them. `just check-contracts` runs in CI
and fails the build if the committed files are not reproducible from the backend.

### Consequences

- Good, because a backend change that alters the wire format shows up as a diff in
  `contracts/`, so API changes are visible and reviewable in the PR that causes
  them.
- Good, because drift between the two sides is caught in CI rather than at runtime.
- Good, because the frontend can build without a running backend — the contracts
  are just files in the repo.
- Bad, because contributors must remember to regenerate after protocol changes;
  the CI check is the backstop that makes forgetting a failed build rather than a
  latent bug.
- Neutral, because the generated files add noise to some diffs; they are marked as
  generated and are not edited by hand.
