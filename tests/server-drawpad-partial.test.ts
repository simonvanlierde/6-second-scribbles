/* eslint-disable @typescript-eslint/no-explicit-any */

import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'



describe('server partial stroke relay', () => {
  it('broadcasts draw_stroke_partial to clients', () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)
    const c1 = createMockConnection('c1', room)
    const c2 = createMockConnection('c2', room)

    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), c1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), c2)

    const partial = {
      type: 'draw_stroke_partial',
      playerId: 'p2',
      stroke: { color: '#0f0', width: 2, points: [{ x: 1, y: 1 }] },
    }
    server.onMessage(JSON.stringify(partial), c2)

    const broadcasts = (room as any).getBroadcasts()
    expect(broadcasts.some((b: string) => b.includes('draw_stroke_partial'))).toBe(true)
  })
})
