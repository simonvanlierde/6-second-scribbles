# Contracts

This folder holds the published boundary contract for realtime room traffic.

- `catalog/room-events.json`
  Contract-first event inventory and grouping metadata.
- `asyncapi/room-websocket.asyncapi.yaml`
  Generated consumer-facing websocket contract document.
- `asyncapi/room-websocket.metadata.json`
  Structured metadata used to generate the AsyncAPI document.
- `examples/client-events.json`
  Representative client-to-server event examples.
- `examples/server-events.json`
  Representative server-to-client event examples.
- `jsonschema/client-event.schema.json`
  Generated client-to-server message schema.
- `jsonschema/server-event.schema.json`
  Generated server-to-client message schema.

Current workflow:

1. `contracts/catalog/room-events.json` is the source of truth for event inventory and grouping.
2. `backend/app/rooms/protocol.py` remains the implementation source of truth for payload shapes.
3. `backend/scripts/generate_protocol_contracts.py` exports stable JSON Schema artifacts into `contracts/jsonschema/`.
4. `frontend/scripts/generate-asyncapi.mjs` generates the AsyncAPI document from contract metadata, catalog data, and examples.
5. `frontend/scripts/generate-types.mjs` generates runtime Zod validators and TypeScript types from those contract artifacts.
6. `frontend/scripts/validate-contracts.mjs` validates the catalog, AsyncAPI refs, and example payloads against the published schemas.

Commands:

- `npm run generate:contracts`
- `npm run check:contracts`
- `cd frontend && npm run generate:asyncapi`
- `npm run generate:types`
- `cd frontend && npm run validate:contracts`
- `just contracts`
