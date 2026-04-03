# Contracts

This folder holds the published realtime wire contract.

What matters:

- `backend/app/rooms/protocol.py`
  Source of truth for websocket payload shapes.
- `jsonschema/`
  Generated machine-readable contract artifacts. This is the important output.
- `room-events.json`
  Small human-authored event metadata for grouping and summaries.
- `client-events.examples.json` and `server-events.examples.json`
  Representative payload fixtures used for docs and validation.
- `room-websocket.metadata.json`
  Small metadata file used to generate the AsyncAPI document.
- `room-websocket.asyncapi.yaml`
  Generated websocket API document for humans and tooling.

Pipeline:

1. Backend models generate JSON Schema into `contracts/jsonschema/`.
2. Frontend types and Zod validators are generated from those schemas.
3. AsyncAPI is generated from the schemas, event metadata, and examples.
4. Validation checks that the generated schemas, examples, and AsyncAPI stay in sync.

Use these commands:

- `npm run contracts:generate`
  Regenerate JSON Schema and AsyncAPI.
- `npm run contracts:types`
  Regenerate JSON Schema, AsyncAPI, and frontend protocol types.
- `npm run contracts:validate`
  Regenerate everything needed, then validate schemas, examples, and AsyncAPI refs.
- `npm run contracts:check`
  Assert that generated contract files are already up to date.
- `just contracts`
  Shortcut for `npm run contracts:types`.
