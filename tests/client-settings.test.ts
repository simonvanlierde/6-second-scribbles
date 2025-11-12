/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'

describe('client settings handler', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('applies settings_update to the store and persists', () => {
    const store = useGameStore()
    store.localPlayerId = 'p2'
    store.localPlayerName = 'Player'

    const { handleMessage } = useGameConnection()

    const msg = { type: 'settings_update', difficulty: 'hard', rounds: 8, roundLength: 75 }
    handleMessage(msg as any)

    expect(store.difficulty).toBe('hard')
    expect(store.maxRounds).toBe(8)
    expect(store.roundLength).toBe(75)
  })
})
