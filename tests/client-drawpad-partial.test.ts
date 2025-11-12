/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'

describe('client partial draw handler', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('adds remote partials but ignores local-origin partials', () => {
    const store = useGameStore()
    store.localPlayerId = 'p1'

    const { handleMessage } = useGameConnection()

    // Remote partial
    handleMessage({ type: 'draw_stroke_partial', playerId: 'p2', stroke: { color: '#123', width: 2, points: [{ x: 1, y: 2 }] } } as any)
    expect(store.currentStrokes.length).toBeGreaterThan(0)

    const before = store.currentStrokes.length

    // Local-origin partial should be ignored
    handleMessage({ type: 'draw_stroke_partial', playerId: 'p1', stroke: { color: '#123', width: 2, points: [{ x: 3, y: 4 }] } } as any)
    expect(store.currentStrokes.length).toBe(before)
  })
})
