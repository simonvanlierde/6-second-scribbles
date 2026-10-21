# Contracts

Generated contract files that the backend and frontend share. Don't edit them by
hand. [ADR 0001](../docs/adr/0001-committed-generated-contracts.md) explains why
they are committed.

- `openapi.json`: exported HTTP API schema
- `jsonschema/`: JSON Schema files for client and server WebSocket messages

The backend exports these from its route, schema, and room protocol code. The
frontend generates TypeScript and Zod types from them.

From the repository root:

```bash
just generate-contracts    # or: pnpm run contracts:generate
just check-contracts       # or: pnpm run contracts:check
```
