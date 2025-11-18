import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import FinalResultsView from '@/views/room/FinalResultsView.vue'

const sendMock = vi.fn()

// Mocked store matching interface used by FinalResultsView
const storeMock = {
  getFinalScores: () => [
    { playerId: 'p1', playerName: 'Alice', score: 10 },
    { playerId: 'p2', playerName: 'Bob', score: 10 },
    { playerId: 'p3', playerName: 'Carol', score: 5 },
  ],
  readyCount: 0,
  totalPlayers: 3,
  isHost: false,
  localPlayerId: 'p1',
  playersList: [{}, {}, {}],
  maxRounds: 3,
  difficulty: 'normal',
  gamePhase: 'final-results',
  reset: () => {},
}

vi.mock('@/composables/useGameConnection', () => ({ useGameConnection: () => ({ send: sendMock, disconnect: vi.fn() }) }))
vi.mock('@/stores/game', () => ({ useGameStore: () => storeMock }))

describe('FinalResultsView DOM', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders tied winners and dense ranks correctly', async () => {
    // stub out ConfirmDialog and FontAwesomeIcon
    const ConfirmDialogStub = defineComponent({ name: 'ConfirmDialog', props: ['modelValue'], setup: () => () => h('div') })
    const FaStub = defineComponent({ name: 'FontAwesomeIcon', props: ['icon'], setup: () => () => h('i') })

    const wrapper = mount(FinalResultsView, {
      global: { components: { ConfirmDialog: ConfirmDialogStub, 'font-awesome-icon': FaStub } },
    })

    await wrapper.vm.$nextTick()

    // Winner header should include both Alice and Bob
    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).toContain('Bob')
    expect(wrapper.find('.tie-note').exists()).toBe(true)

    // There should be two items with rank '1'
    const ranks = wrapper.findAll('.rank')
    const rankTexts = ranks.map((r) => r.text())
    // first two ranks should start with '1'
    expect(rankTexts[0].startsWith('1')).toBe(true)
    expect(rankTexts[1].startsWith('1')).toBe(true)
  })
})
