/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */
import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'

// Minimal mock connection
function createMockConnection(id: string) {
  return {
    id,
    send: (_msg: string) => {},
    close: () => {},
  }
}

// Minimal mock room with broadcast capture
function createMockRoom() {
  const broadcasted: string[] = []
  return {
    id: 'test-room',
    storage: { setAlarm: async () => {} },
    broadcast: (msg: string) => broadcasted.push(msg),
    getBroadcasts: () => broadcasted,
  }
}

describe('GameServer drawpad relay', () => {
  it('relays draw_stroke to all clients', () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1')
    const conn2 = createMockConnection('c2')

    // Simulate two players joining
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // p2 sends a stroke
    const strokeMsg = { type: 'draw_stroke', playerId: 'p2', stroke: { color: '#000', width: 3, points: [{ x: 1, y: 2 }] } }
    server.onMessage(JSON.stringify(strokeMsg), conn2)

    const broadcasts = (room as any).getBroadcasts()
    // Expect that the draw_stroke was broadcast
    expect(broadcasts.some((b: string) => b.includes('draw_stroke'))).toBe(true)
  })

  it('only accepts drawpad_clear from host', () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1')
    const conn2 = createMockConnection('c2')

    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // Set host
    server.hostId = 'p1'

    // Non-host tries to clear
    server.onMessage(JSON.stringify({ type: 'drawpad_clear', playerId: 'p2' }), conn2)
    let broadcasts = (room as any).getBroadcasts()
    // No broadcast expected
    expect(broadcasts.some((b: string) => b.includes('drawpad_clear'))).toBe(false)

    // Host clears
    server.onMessage(JSON.stringify({ type: 'drawpad_clear', playerId: 'p1' }), conn1)
    broadcasts = (room as any).getBroadcasts()
    expect(broadcasts.some((b: string) => b.includes('drawpad_clear'))).toBe(true)
  })
})
