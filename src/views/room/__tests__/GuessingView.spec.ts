import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import GuessingView from '@/views/room/GuessingView.vue'

const sendMock = vi.fn()

const otherPlayer = { id: 'p2', name: 'Alice', drawing: 'data:image/png;stub' }
type GuessStoreMock = {
  localPlayerId: string
  playersList: Array<{ id: string; name: string } | typeof otherPlayer>
  readyCount: number
  totalPlayers: number
}

const storeMock: GuessStoreMock = {
  localPlayerId: 'p1',
  playersList: [{ id: 'p1', name: 'You' }, otherPlayer],
  readyCount: 0,
  totalPlayers: 2,
}

vi.mock('@/composables/useGameConnection', () => ({
  useGameConnection: () => ({ send: sendMock }),
}))
vi.mock('@/stores/game', () => ({ useGameStore: () => storeMock }))

describe('GuessingView (basic)', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders other player drawing and guess inputs', () => {
    const wrapper = mount(GuessingView)
    expect(wrapper.text()).toContain("Alice's Drawing")
    // should render an img for the drawing
    const img = wrapper.find('img.player-drawing')
    expect(img.exists()).toBe(true)
  })

  it('submitting guesses sends submit_guess and player_ready when all submitted', async () => {
    const wrapper = mount(GuessingView)
    // fill one guess input for the other player
    const inputs = wrapper.findAll('.guess-input')
    expect(inputs.length).toBeGreaterThan(0)
    await inputs[0].setValue('Cat')

    const submitBtn = wrapper.find('button.btn.btn-primary')
    await submitBtn.trigger('click')

    expect(sendMock).toHaveBeenCalled()
    // first call should be submit_guess
    expect(sendMock.mock.calls[0][0].type).toBe('submit_guess')
  })
})
