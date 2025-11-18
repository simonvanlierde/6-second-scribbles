/* eslint-disable @typescript-eslint/no-explicit-any */

import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'

// This test verifies that when the last player leaves the server schedules a
// delayed stale marker and that reconnecting within the delay cancels it.

describe('GameServer room stale marking behavior', () => {
  it('marks room as stale after delay when room empties', async () => {
    // Speed up the stale marking for tests so we don't hit the test timeout
    ;(GameServer as any).STALE_MARK_DELAY_MS = 100

    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    // Make two connections join and cause host to be set
    const c1 = createMockConnection('c1', room)
    const c2 = createMockConnection('c2', room)
    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), c1)
    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), c2)

    // Persist something to storage so we can verify it's NOT reset
    await server.storage.set('difficulty', 'hard')
    const before = (room.storage as any)._data.get('difficulty')
    expect(before).toBe('hard')

    // Simulate both players disconnecting (and PartyKit removing connections)
    await server.onClose(c1)
    // Mock runtime would remove the connection from the room; emulate that here
    ;(room as any)._connections = (room as any)._connections.filter((c: any) => c.id !== c1.id)
    await server.onClose(c2)
    ;(room as any)._connections = (room as any)._connections.filter((c: any) => c.id !== c2.id)

    // Wait slightly longer than the configured delay
    const waitMs = (GameServer as any).STALE_MARK_DELAY_MS + 50
    await new Promise((r) => setTimeout(r, waitMs))

    // Storage should still have our value (NOT reset)
    const after = (room.storage as any)._data.get('difficulty')
    expect(after).toBe('hard')

    // But room should be marked as stale
    const staleMarker = (room.storage as any)._data.get('_stale')
    expect(staleMarker).toBeDefined()
    expect(staleMarker.abandoned_at).toBeTypeOf('number')
  })

  it('cancels scheduled stale marker when a connection rejoins', async () => {
    // Speed up the stale marking for tests so we don't hit the test timeout
    ;(GameServer as any).STALE_MARK_DELAY_MS = 100

    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const c1 = createMockConnection('c1', room)
    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), c1)

    await server.storage.set('difficulty', 'easy')

    // Disconnect the only player to schedule a stale marker
    await server.onClose(c1)
    ;(room as any)._connections = (room as any)._connections.filter((c: any) => c.id !== c1.id)

    // Reconnect before the delay elapses
    const reconnectDelay = ((GameServer as any).STALE_MARK_DELAY_MS as number) - 50
    await new Promise((r) => setTimeout(r, reconnectDelay))

    const c2 = createMockConnection('c2', room)
    server.onConnect(c2)

    // Wait slightly longer than the original delay to ensure stale marker would have fired
    await new Promise((r) => setTimeout(r, 100))

    // Storage should still have our value
    const val = (room.storage as any)._data.get('difficulty')
    expect(val).toBe('easy')

    // Room should NOT be marked as stale because timer was cancelled
    const staleMarker = (room.storage as any)._data.get('_stale')
    expect(staleMarker).toBeUndefined()
  })
})
