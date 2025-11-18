/* eslint-disable @typescript-eslint/no-explicit-any */

import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'

// Minimal mock connection

// Minimal mock room with broadcast capture

describe('GameServer drawpad relay', () => {
  it('relays draw_stroke to all clients', () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1', room)
    const conn2 = createMockConnection('c2', room)

    // Simulate two players joining
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // p2 sends a stroke
    const strokeMsg = {
      type: 'draw_stroke',
      playerId: 'p2',
      stroke: { color: '#000', width: 3, points: [{ x: 1, y: 2 }] },
    }
    server.onMessage(JSON.stringify(strokeMsg), conn2)

    const broadcasts = (room as any).getBroadcasts()
    // Expect that the draw_stroke was broadcast
    expect(broadcasts.some((b: string) => b.includes('draw_stroke'))).toBe(true)
  })

  it('only accepts drawpad_clear from host', async () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1', room)
    const conn2 = createMockConnection('c2', room)

    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // Set host
    server.state.hostId = 'p1'

    // Non-host tries to clear
    await server.onMessage(JSON.stringify({ type: 'drawpad_clear', playerId: 'p2' }), conn2)
    let broadcasts = (room as any).getBroadcasts()
    // No broadcast expected
    expect(broadcasts.some((b: string) => b.includes('drawpad_clear'))).toBe(false)

    // Host clears
    await server.onMessage(JSON.stringify({ type: 'drawpad_clear', playerId: 'p1' }), conn1)
    broadcasts = (room as any).getBroadcasts()
    expect(broadcasts.some((b: string) => b.includes('drawpad_clear'))).toBe(true)
  })
})
