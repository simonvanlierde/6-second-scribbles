import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'
/* eslint-disable @typescript-eslint/no-explicit-any */

describe('GameServer settings persistence', () => {
  it('persists settings into room.metadata and includes them in room_state on connect', async () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const conn1 = createMockConnection('c1', room)
    const conn2 = createMockConnection('c2', room)

    // Simulate player join messages
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), conn1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), conn2)

    // Set host (now in server.state, not server.hostId)
    server.state.hostId = 'p1'

    // Host sends a settings_update
    const settingsMsg = { type: 'settings_update', difficulty: 'hard', rounds: 7, roundLength: 90 }
    await server.onMessage(JSON.stringify(settingsMsg), conn1)

    // Verify state updated
    expect(server.state.difficulty).toBe('hard')
    expect(server.state.maxRounds).toBe(7)
    expect(server.state.roundLength).toBe(90)

    // New connection should receive room_state containing these settings
    const conn3 = createMockConnection('c3', room)
    // We'll capture what conn3.send would receive by overriding it
    let lastMsg = ''
    conn3.send = (m: string) => {
      lastMsg = m
    }
    server.onConnect(conn3)

    const parsed = JSON.parse(lastMsg)
    expect(parsed.type).toBe('room_state')
    expect(parsed.difficulty).toBe('hard')
    expect(parsed.maxRounds).toBe(7)
    expect(parsed.roundLength).toBe(90)
  })
})
