import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'
/* eslint-disable @typescript-eslint/no-explicit-any */

// Minimal mock connection

// Minimal mock room with broadcast, storage, and getConnections

describe('GameServer host transfer preserves settings', () => {
  it('retains room metadata when host leaves and new host is assigned', () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1', room)
    const conn2 = createMockConnection('c2', room)

    // Simulate player join messages
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // Set host and send settings_update
    server.state.hostId = 'p1'
    const settingsMsg = { type: 'settings_update', difficulty: 'hard', rounds: 6, roundLength: 45 }
    server.onMessage(JSON.stringify(settingsMsg), conn1)

    // Now simulate host disconnect
    server.onClose(conn1 as any)

    // New host should be p2
    expect(server.state.hostId).toBe('p2')

    // Ensure settings persisted in room metadata
    expect(server.state.difficulty).toBe('hard')
    expect(server.state.maxRounds).toBe(6)
    expect(server.state.roundLength).toBe(45)
  })
})
