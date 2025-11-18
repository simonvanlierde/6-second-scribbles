import { describe, expect, it } from 'vitest'

import computeDenseRanks, { RankedItem } from '@/utils/ranking'

describe('computeDenseRanks', () => {
  it('assigns dense ranks and marks ties correctly', () => {
    const scores = [
      { playerId: 'a', playerName: 'Alice', score: 10 },
      { playerId: 'b', playerName: 'Bob', score: 15 },
      { playerId: 'c', playerName: 'Carol', score: 15 },
      { playerId: 'd', playerName: 'Dan', score: 8 },
      { playerId: 'e', playerName: 'Eve', score: 8 },
      { playerId: 'f', playerName: 'Frank', score: 5 },
    ]

    const ranked = computeDenseRanks(scores)

    // Expected order: Bob (15,r1), Carol (15,r1 tied), Alice (10,r2), Dan (8,r3), Eve (8,r3 tied), Frank (5,r4)
  const summary: { id: string; rank: number; tied: boolean }[] = ranked.map((r: RankedItem) => ({ id: r.player.playerId, rank: r.rank, tied: r.tiedWithPrevious }))
    expect(summary).toEqual([
      { id: 'b', rank: 1, tied: false },
      { id: 'c', rank: 1, tied: true },
      { id: 'a', rank: 2, tied: false },
      { id: 'd', rank: 3, tied: false },
      { id: 'e', rank: 3, tied: true },
      { id: 'f', rank: 4, tied: false },
    ])
  })
})
