# 6 Second Scribbles - Architecture Documentation

## State Management Strategy

### Server (PartyKit Room) - Source of Truth

The PartyKit room is the **single source of truth** for all room-level game state.

#### State Storage Locations

**`Room.storage` (Persistent, survives hibernation):**

- `gamePhase`: 'waiting-room' | 'drawing' | 'guessing' | 'scoring' | 'complete'
- `difficulty`: string
- `maxRounds`: number
- `roundLength`: number (seconds)
- `currentRound`: number
- `roundStartTime`: number (timestamp)
- `hostId`: string
- `sharedPadStrokes`: DrawStroke[]
- `sharedPadVisibility`: boolean
- `playerScores`: Record<playerId, number>
- `readyPlayers`: Set<playerId>
- `pendingIdle`: Record<playerId, timestamp>

**`Connection.state` (Per-connection, ephemeral):**

- `playerId`: string
- `name`: string

**In-memory only (acceptable to lose on hibernation):**

- `players: Map<playerId, Player>` - Rebuilt from connections on `onStart()`
- `lastActivity` per player - Rebuilt on reconnection

### Client (Pinia Store) - Reactive Cache

The client-side Pinia store is a **reactive cache** of server state.

#### State Storage Locations

**Pinia Store (in-memory, reactive):**

- All room state received from server messages
- Updated when receiving WebSocket messages from server
- **Never persisted to localStorage** (except player name)

**localStorage (minimal, player-specific only):**

- `playerName`: string - User's display name
- ~~`gameState`~~ - **REMOVED** - Don't persist room state locally

#### Client State Flow

```
Server WebSocket Message → Pinia Store → Vue Components
```

1. Client connects to room
2. Server sends `room_state` message with complete state
3. Client updates Pinia store with received state
4. Components react to store changes
5. User actions → WebSocket messages to server
6. Server broadcasts updates → All clients update their stores

### Key Principles

1. **Server is Source of Truth**: All authoritative state lives in PartyKit Room
2. **No Client-Side State Persistence**: Don't save room state in localStorage
3. **Optimistic Updates**: Client can update UI immediately, but server confirms
4. **Reconnection**: On reconnect, request full state from server
5. **Per-Room State**: Each PartyKit room instance manages one game room
6. **Per-Player Identity**: Stored in Connection.state, survives connection but not hibernation

## Current Issues to Fix

### Issue 1: `this.room.metadata` Not Persisted

**Problem**: Using in-memory `this.room.metadata` object which is lost on hibernation

**Solution**: Move all `room.metadata` fields to `Room.storage`:

```typescript
// BAD (current)
this.room.metadata.gamePhase = 'drawing'

// GOOD (use Room.storage)
await this.room.storage.put('gamePhase', 'drawing')
const gamePhase = await this.room.storage.get<string>('gamePhase')
```

### Issue 2: Client Store Saves to localStorage

**Problem**: `src/stores/game.ts` saves room state to localStorage in `saveState()`

**Solution**: Remove `saveState()` calls and localStorage persistence of room state

- Keep only `localStorage.setItem('playerName', name)` for player name
- Remove all `initialState` loading from localStorage
- Trust server as source of truth

### Issue 3: Unclear Room vs Player State

**Problem**: GameStore mixes room-level and player-specific state

**Solution**: Clearly separate:

- **Room state**: Synced from server, read-only from client perspective
- **Player state**: `localPlayerId`, `localPlayerName` - only these persist locally

## Migration Plan

1. ✅ Document current architecture
2. Update server to use `Room.storage` instead of `this.room.metadata`
3. Update server `onStart()` to load from `Room.storage`
4. Remove localStorage persistence from client store (except playerName)
5. Update client to request state on mount
6. Test reconnection scenarios
