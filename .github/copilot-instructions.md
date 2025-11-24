## 6 Second Scribbles – AI Coding Agent Guide

Concise, project-specific conventions to be productive quickly. Focus on existing patterns; do not introduce new architectural concepts without user approval.

### Big Picture

- Real-time multiplayer drawing/guessing game (Vue 3 + Pinia + PartyKit).
- Server (`src/server/`) is a “dumb pipe”: mostly relays messages, minimal game logic; authoritative for room-level metadata persistence via `Room.storage` (wrapped by `RoomStorage`).
- Client contains almost all game flow logic (round start, scoring, transitions) inside composables + Pinia store + a client-side GameEngine (see `src/composables/gameEngineInstance.ts`).
- State flow: Server broadcasts → `useGameConnection` parses & normalizes → Pinia store (`game.ts`) → Vue views/components.

### Source of Truth & State

- Authoritative room/game state lives on server in `Room.storage` (see `ARCHITECTURE.md`). Treat client store as a reactive cache.
- Local persistence: ONLY `playerName` in `localStorage`. (Current store still persists broader `gameState`; future changes aim to remove that — do not extend persistence.)
- Schema validation: All inbound server metadata passes through `RoomStateSchema` / `normalizeRoomMetadata` in `src/shared/schemas/room.ts` before mutating store.

### Messaging Contract (WebSocket)

- Message union defined in `src/server/index.ts` (`GameMessage`). Examples: `join`, `room_state`, `player_joined`, `start_game`, `start_round`, `submit_guess`, `draw_stroke`, `draw_stroke_partial`, `drawpad_clear`, `pad_visibility`, `settings_update`, `restart_game`, heartbeat & idle flow (`idle_prompt`, `idle_confirm`, `kicked`).
- Server adds `roundStartTime` on `start_round`; client trusts that timestamp.
- Rate limiting per connection implemented in server `onMessage` (simple sliding window). When adding new high-frequency message types, update `TYPE_LIMITS` accordingly.

### Server Conventions (`src/server/`)

- Persist only necessary fields via `RoomStorage.savePartial`; volatile recalculations allowed during `onStart()`.
- Host authority: actions like `settings_update`, `drawpad_clear`, `pad_visibility`, `drawpad_restore` gated by comparing sender connection’s `playerId` to current `hostId`.
- Idle management delegated to `IdleChecker` (keep separation of concerns: don’t merge idle logic into main server class).
- Prefer broadcasting original message payload unless server must augment (e.g. inject `roundStartTime`).

### Client Conventions

- Connection lifecycle & parsing in `useGameConnection.ts`; avoid duplicating socket listeners elsewhere.
- Always send messages via `send()` wrapper (buffers pre-open using PartySocket).
- Game phase routing: Views react to `gamePhase` in store; do not manually push routes in message handlers except initial lobby redirects.
- Store (`game.ts`) handles score aggregation, phase transitions, stroke accumulation. Future refactor will remove broad `saveState()` persistence—avoid adding new keys there.
- Shared canvas strokes: host clearing or visibility changes propagate via dedicated message types; clients mirror host intent and forcibly sync local pad visibility.

### Drawing & Fuzzy Matching

- Strokes: full vs partial: partial messages (`draw_stroke_partial`) represent incremental points; treat uniformly when updating waiting-room canvas.
- Eraser implemented as white stroke overlay (no stroke deletion logic). Don’t reintroduce remove-by-id.
- Fuzzy guessing: `utils/fuzzy.ts` uses Fuse.js; threshold defaults `0.35`, acceptance score `>=0.7`. When adjusting guess tolerance, modify these constants centrally.

### Testing & Environments

- Unit tests (Vitest): globs in `vitest.config.ts` include `src/**/*.spec.*`, `src/**/__tests__/**`, and `tests/**/*.test.*`.
- E2E tests (Playwright) live in `e2e/`; run with `npm run test:e2e` (auto launches dev or preview server per config).
- Avoid network mocking inside unit tests; prefer direct invocation of composables/store methods with crafted messages via `handleMessage()` (exported in `useGameConnection`).
- When creating tests for new message types, simulate receipt by calling `handleMessage(parsedMessage)` rather than opening a real socket.

### Build & Dev Workflows

- Combined dev: `npm run dev` (runs Vite + PartyKit via `concurrently`). Use separate scripts only when isolating issues: `dev:web` / `dev:server`.
- Production build: `npm run build` (client only). Deploy server separately via `npm run deploy:server`.
- Type safety: run `npm run type-check` (Vue TSC) before large refactors.
- Linting: `npm run lint` (oxlint + ESLint). Formatting: `npm run format`.

### Performance & Rate Limits

- High-volume draw events already optimized (partial strokes). Don’t introduce per-point acknowledgements.
- Keep added messages small & JSON-serializable; avoid sending binary blobs.
- Respect existing `TYPE_LIMITS` if introducing new streaming actions.

### Extension & Modification Guidelines

- Add server-side logic only when authoritative consistency or cheating prevention requires it; otherwise keep logic client-side for mobility.
- Reuse `normalizeRoomMetadata` for any new persisted fields to maintain resilience against malformed data.
- For new UI state that derives exclusively from persisted server fields, extend schema + storage, then hydrate through existing `room_state` path (avoid ad-hoc messages).
- For ephemeral client-only helpers (timers, local toggles), store outside persisted payload; do not add to `RoomStateSchema` unless needed cross-client.

### Logging

- Use `src/utils/logger.ts` (pino + pretty) on server/client; prefer structured objects for state summaries (see existing `logger.info('[WebSocket] Synced room state…')`). Avoid console.\* directly in new code.

### Do Not

- Do not persist full room/game state to client localStorage (only `playerName`).
- Do not move core game flow into server prematurely or duplicate message handling logic in components.
- Do not bypass schema validation when applying server metadata to store.

### Quick Reference

| Task                  | Command                 |
| --------------------- | ----------------------- |
| Dev (frontend+server) | `npm run dev`           |
| Unit tests            | `npm run test:unit`     |
| E2E tests             | `npm run test:e2e`      |
| Type check            | `npm run type-check`    |
| Lint                  | `npm run lint`          |
| Format                | `npm run format`        |
| Build (client)        | `npm run build`         |
| Deploy server         | `npm run deploy:server` |

### Feedback Needed

Clarify if planned removal of broad localStorage persistence is already approved; confirm any upcoming migration of client GameEngine logic to server before refactoring message types.
