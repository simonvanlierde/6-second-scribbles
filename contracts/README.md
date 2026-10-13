# Contracts

This directory holds the generated contract files that the backend and frontend share.

These files are committed to git. So an API change shows up in review, and the frontend has a fixed input to generate its code from.

## What Lives Here

- `openapi.json`: exported HTTP API schema
- `room-events.json`: high-level room event definitions
- `jsonschema/`: JSON Schema files for client and server WebSocket messages

## Source Of Truth

These files are generated from backend code:

- HTTP models come from the backend's route and schema definitions
- WebSocket message schemas come from the room protocol code

Don't edit the generated files in this directory by hand.

## Workflow

1. The backend exports the API and protocol schemas into `contracts/`
2. The frontend generates TypeScript and Zod types from those files
3. The contract check confirms that regenerating gives the same files as the committed ones

## Commands

From the repository root:

```bash
just generate-contracts
just check-contracts
```

The same two steps also run through `pnpm`:

```bash
pnpm run contracts:generate
pnpm run contracts:check
```
