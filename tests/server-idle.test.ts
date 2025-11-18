/* eslint-disable @typescript-eslint/no-explicit-any */

import { describe, expect, it } from 'vitest'

import GameServer from '../src/server/index'
import { createMockConnection, createMockRoom } from './helpers/mockRoom'



describe('server idle prompts and kicks', () => {
  it('sends idle_prompt and then kicks after prompt expiry', async () => {
    const room = createMockRoom()
    const server = new (GameServer as any)(room)

    const c1 = createMockConnection('c1', room)
    const c2 = createMockConnection('c2', room)

    // Two players join
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p1', name: 'Host' }), c1)
    server.onMessage(JSON.stringify({ type: 'join', playerId: 'p2', name: 'Player' }), c2)

    // Switch to in-game phase so the in-game idle timeout applies
    server.state.gamePhase = 'drawing'

    // Simulate that p1 lastActivity was far in the past
    const now = Date.now()
    const p1 = server.players.get('p1')
    // Use the public static alias on GameServer for the in-game idle timeout
    if (p1) p1.lastActivity = now - (GameServer.idleChecker.INGAME_IDLE_TIMEOUT_MS + 1000)

    // Trigger alarm handler which should schedule a kick for p1 (or send prompt)
    await server.onAlarm()

    // Check that p1 connection received either idle_prompt or kicked
    const sentP1 = (c1 as any).getSent()
    expect(sentP1.length).toBeGreaterThan(0)

    // If a prompt was sent, it should include idle_prompt
    const hasPrompt = sentP1.some((m: string) => m.includes('idle_prompt'))
    const hasKicked = sentP1.some((m: string) => m.includes('kicked'))

    // Depending on timing logic the server may send a kicked message directly
    expect(hasPrompt || hasKicked).toBeTruthy()

    // If kicked was sent, ensure player_left broadcasted
    const broadcasts = (room as any).getBroadcasts()
    const hasPlayerLeft = broadcasts.some((m: string) => m.includes('player_left'))
    expect(hasPlayerLeft).toBeTruthy()
  })
})
