# Contracts

This directory stores the committed contract artifacts shared by the backend and frontend.

Keeping these files in version control makes API changes visible in reviews and gives the frontend a stable input for code generation.

## What Lives Here

- `openapi.json`: exported HTTP API schema
- `room-events.json`: high-level room event definitions
- `jsonschema/`: JSON Schema files for client and server WebSocket messages

## Source Of Truth

These files are generated from backend code:

- HTTP models come from backend route and schema definitions
- WebSocket message schemas come from the room protocol implementation

The generated files in this directory should not be edited by hand.

## Workflow

1. The backend exports API and protocol artifacts into `contracts/`
2. The frontend generates TypeScript and Zod types from those artifacts
3. Contract checks verify that the committed files are reproducible

## Commands

From the repository root:

```bash
just generate-contracts
just check-contracts
```

Compatibility scripts are also available through `pnpm`:

```bash
pnpm run contracts:generate
pnpm run contracts:check
```
