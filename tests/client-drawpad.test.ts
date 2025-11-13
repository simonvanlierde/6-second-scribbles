/* eslint-disable @typescript-eslint/no-explicit-any */

import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'

describe('client drawpad handler', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('applies draw_stroke to the store', () => {
    const store = useGameStore()
    const { handleMessage } = useGameConnection()

    const msg = {
      type: 'draw_stroke',
      playerId: 'p2',
      stroke: { color: '#000', width: 2, points: [{ x: 1, y: 2 }] },
    }
    handleMessage(msg as any)

    expect(store.currentStrokes.length).toBeGreaterThan(0)
    expect(store.currentStrokes[0]!.color).toBe('#000')
  })
})
