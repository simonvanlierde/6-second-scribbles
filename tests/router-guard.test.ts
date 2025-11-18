import { describe, expect, it, vi } from 'vitest'

// Ensure vue-router real exports are available (some test environments partially mock it)
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal()
  return { ...actual }
})

// Mock the game store before importing the router so the guard uses the mock
type MockStore = {
  roomCode: string
  gamePhase?: string | undefined
  setRoomCode: (c: string) => void
  setGamePhase: (p: string) => void
}

const mockStore: MockStore = {
  roomCode: '',
  gamePhase: undefined,
  setRoomCode: (c: string) => {
    mockStore.roomCode = c
  },
  setGamePhase: (p: string) => {
    mockStore.gamePhase = p
  },
}

vi.mock('../src/stores/game', () => ({
  useGameStore: () => mockStore,
}))

// Mock the connection so requestGameState sets the store state
vi.mock('../src/composables/useGameConnection', () => ({
  useGameConnection: () => ({
    isConnected: { value: false },
    connect: (roomCode: string) => {
      mockStore.roomCode = roomCode
    },
    requestGameState: async () => {
      // simulate server returning drawing phase
      mockStore.roomCode = 'test-room'
      mockStore.gamePhase = 'drawing'
    },
  }),
}))

import router from '../src/router'

describe('router guard', () => {
  it('hydrates state and redirects to server phase when visiting a room route', async () => {
    await router.push('/room/test-room/drawing')
    // wait for navigation to settle
    await router.isReady()
    expect(router.currentRoute.value.name).toBe('drawing')
  })
})
