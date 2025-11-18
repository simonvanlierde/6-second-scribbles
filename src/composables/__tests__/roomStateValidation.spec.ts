import { describe, expect, it } from 'vitest'

import { useGameConnection } from '@/composables/useGameConnection'
import { normalizeRoomMetadata, RoomStateSchema } from '@/shared/schemas/room'
import { useGameStore } from '@/stores/game'

// Lightweight test to ensure validation helpers work and client handler tolerates malformed metadata
describe('room_state validation', () => {
  it('RoomStateSchema.safeParse should fail on malformed metadata but normalizeRoomMetadata returns defaults', () => {
    const malformed: Record<string, unknown> = {
      gamePhase: 'unknown-phase',
      difficulty: 123,
      maxRounds: 'not-a-number',
      roundLength: '10',
      sharedPadVisibility: 'yes',
      sharedPadStrokes: 'not-an-array',
      hostId: 42,
    }

    const parsed = RoomStateSchema.safeParse(malformed)
    expect(parsed.success).toBe(false)

    const normalized = normalizeRoomMetadata(malformed)
    expect(normalized).toHaveProperty('gamePhase')
    expect(normalized.gamePhase).toBeDefined()
    expect(typeof normalized.maxRounds).toBe('number')
  })

  it('client handleMessage should not throw when given malformed room_state', () => {
    // Prepare a minimal message that the client would receive
    const msg = {
      type: 'room_state',
      players: [{ id: 'p1', name: 'Alice' }],
      categories: ['c1'],
      gamePhase: 'drawing',
      roundLength: '10', // string that should be coerced
      difficulty: 'easy',
      maxRounds: '3',
      sharedPadVisibility: 'true', // malformed
      sharedPadStrokes: [],
      hostId: 'p1',
    }

    const conn = useGameConnection()
    // call handleMessage directly and ensure it doesn't throw
    expect(() => conn.handleMessage(msg)).not.toThrow()

    // Verify store was updated (useGameStore is a pinia store; just check that it has players)
    const store = useGameStore()
    expect(store.playersList.some((p: { id: string }) => p.id === 'p1')).toBe(true)
  })
})
