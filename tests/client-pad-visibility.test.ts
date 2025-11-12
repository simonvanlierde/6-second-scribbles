/* eslint-disable @typescript-eslint/no-explicit-any */
/* eslint-disable import/no-unresolved */
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useGameConnection } from '@/composables/useGameConnection'
import { useGameStore } from '@/stores/game'

describe('client pad visibility', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('applies pad_visibility to the store', () => {
    const store = useGameStore()
    const { handleMessage } = useGameConnection()

    handleMessage({ type: 'pad_visibility', playerId: 'p1', visible: false } as any)
    expect(store.showDrawpad).toBe(false)
  })
})
