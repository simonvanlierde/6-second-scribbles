export interface PlayerScore {
  playerId: string
  playerName: string
  score: number
}

export interface RankedItem {
  player: PlayerScore
  rank: number
  tiedWithPrevious: boolean
}

// Compute dense ranks: if two players tie for a rank, the next player gets rank+1
export function computeDenseRanks(scores: PlayerScore[]): RankedItem[] {
  const sorted = scores.slice().sort((a, b) => b.score - a.score)
  const result: RankedItem[] = []
  let lastScore: number | null = null
  let lastRank = 0
  for (let i = 0; i < sorted.length; i++) {
    const player = sorted[i]
    if (!player) continue
    if (lastScore === null || player.score !== lastScore) {
      // Dense ranking: increment rank by 1 for a new distinct score
      lastRank = lastRank + 1
      result.push({ player, rank: lastRank, tiedWithPrevious: false })
    } else {
      // same score as previous -> tie: same rank as previous
      result.push({ player, rank: lastRank, tiedWithPrevious: true })
    }
    lastScore = player.score
  }
  return result
}

export default computeDenseRanks
