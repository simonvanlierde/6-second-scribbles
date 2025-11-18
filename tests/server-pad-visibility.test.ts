/* eslint-disable @typescript-eslint/no-explicit-any */

import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'

describe('server pad visibility', () => {
  it('persists pad_visibility from host and includes in room_state', async () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const c1 = createMockConnection('c1', room)
    const c2 = createMockConnection('c2', room)

    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), c1)
    await server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), c2)

    server.state.hostId = 'p1'

    await server.onMessage(JSON.stringify({ type: 'pad_visibility', playerId: 'p1', visible: false }), c1)

    expect(server.state.sharedPadVisibility).toBe(false)

    const c3 = createMockConnection('c3', room)
    let last = ''
    c3.send = (m: string) => {
      last = m
    }
    server.onConnect(c3)
    const parsed = JSON.parse(last)
    expect(parsed.type).toBe('room_state')
    expect(parsed.sharedPadVisibility).toBe(false)
  })
})
