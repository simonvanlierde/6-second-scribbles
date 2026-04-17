# Contracts

This folder contains committed generated contract artifacts.

## Source Of Truth

- `backend/app/rooms/protocol.py` for the websocket protocol
- `backend/app/**/schemas.py` for HTTP request and response models exported through OpenAPI

## Pipeline

1. Backend exports websocket JSON Schema into `contracts/jsonschema/`
2. Backend exports HTTP OpenAPI into `contracts/openapi.json`
3. Frontend generates TypeScript and Zod types into `frontend/src/generated/`
4. Validation regenerates into a temporary directory and byte-compares the result against tracked files

## Ownership

- Root `just` commands are the canonical orchestration surface
- `backend/scripts/generate_contracts.py` owns export into `contracts/`
- `frontend/scripts/generate-contracts.mjs` owns frontend codegen from `contracts/`
- Generated artifacts stay committed so local development, reviews, and CI all share the same contract snapshot

## Commands

```bash
just generate-contracts
just check-contracts
```

Compatibility aliases:

```bash
pnpm run contracts:generate
pnpm run contracts:check
```

`pnpm run contracts:check` runs the same verifier used by `just check-contracts`.

Generated files in this folder should not be edited by hand.
