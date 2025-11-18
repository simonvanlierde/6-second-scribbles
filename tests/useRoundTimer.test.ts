import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import { useRoundTimer } from '../src/composables/useRoundTimer'

describe('useRoundTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2025-01-01T00:00:00.000Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('initializes timeLeft to roundLength when no start time', () => {
    const { timeLeft } = useRoundTimer({ roundLength: 60, roundStartTime: undefined })
    expect(timeLeft.value).toBe(60)
  })

  it('computes timeLeft correctly when start time is in the past', () => {
    // start time 10 seconds ago
    const start = Date.now() - 10000
    const { timeLeft } = useRoundTimer({ roundLength: 60, roundStartTime: start })
    expect(timeLeft.value).toBe(50)
  })

  it('computes timeLeft as 0 when start time is far in the past', () => {
    const start = Date.now() - 120000 // 2 minutes ago
    const { timeLeft } = useRoundTimer({ roundLength: 60, roundStartTime: start })
    expect(timeLeft.value).toBe(0)
  })

  it('start() begins ticking and stop() stops it', async () => {
    const startTime = Date.now()
    const { timeLeft, start, stop } = useRoundTimer({ roundLength: 60, roundStartTime: startTime })
    start()
    // advance 3 seconds
    vi.advanceTimersByTime(3000)
    expect(timeLeft.value).toBe(57)
    stop()
    vi.advanceTimersByTime(3000)
    expect(timeLeft.value).toBe(57)
  })
})
