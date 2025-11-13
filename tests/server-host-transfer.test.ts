import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
/* eslint-disable @typescript-eslint/no-explicit-any */

// Minimal mock connection
function createMockConnection(id: string) {
  return {
    id,
    send: (_msg: string) => {},
    close: () => {},
  }
}

// Minimal mock room with broadcast and storage
function createMockRoom() {
  const broadcasted: string[] = []
  return {
    id: 'test-room',
    storage: {
      setAlarm: async () => {},
    },
    broadcast: (msg: string) => broadcasted.push(msg),
    getBroadcasts: () => broadcasted,
  }
}

describe('GameServer host transfer preserves settings', () => {
  it('retains room metadata when host leaves and new host is assigned', () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1')
    const conn2 = createMockConnection('c2')

    // Simulate player join messages
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // Set host and send settings_update
    server.hostId = 'p1'
    const settingsMsg = { type: 'settings_update', difficulty: 'hard', rounds: 6, roundLength: 45 }
    server.onMessage(JSON.stringify(settingsMsg), conn1)

    // Now simulate host disconnect
    server.onClose(conn1 as any)

    // New host should be p2
    expect(server.hostId).toBe('p2')

    // Ensure settings persisted in room metadata
    expect(server.room.metadata.difficulty).toBe('hard')
    expect(server.room.metadata.maxRounds).toBe(6)
    expect(server.room.metadata.roundLength).toBe(45)
  })
})
