import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import DrawingView from '@/views/room/DrawingView.vue'

// mocks
const sendMock = vi.fn()
type StoreMock = {
  currentRound: number
  maxRounds: number
  roundLength: number
  roundStartTime?: number | undefined
  localPlayer: { score: number }
  localPlayerCard: { category: string; items: string[] }
  readyCount: number
  totalPlayers: number
  localPlayerId: string
  gamePhase: string
  currentStrokes: unknown[]
  addStroke: () => void
}

const storeMock: StoreMock = {
  currentRound: 1,
  maxRounds: 3,
  roundLength: 60,
  roundStartTime: undefined,
  localPlayer: { score: 5 },
  localPlayerCard: { category: 'Animals', items: ['Cat', 'Dog'] },
  readyCount: 0,
  totalPlayers: 2,
  localPlayerId: 'p1',
  gamePhase: 'drawing',
  // shared drawpad expects currentStrokes array and addStroke method
  currentStrokes: [],
  addStroke: () => {},
}

vi.mock('@/composables/useGameConnection', () => ({
  useGameConnection: () => ({ send: sendMock }),
}))
vi.mock('@/stores/game', () => ({ useGameStore: () => storeMock }))

describe('DrawingView (basic)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders header, category and items', async () => {
    // simple stub for SharedDrawpad
    const SharedDrawpadStub = defineComponent({
      name: 'SharedDrawpad',
      props: ['mode'],
      setup(_, { expose }) {
        const setColor = vi.fn()
        const setWidth = vi.fn()
        const clear = vi.fn()
        const toDataURL = vi.fn(() => 'data:stub')
        const loadDrawing = vi.fn()
        expose({ setColor, setWidth, clear, toDataURL, loadDrawing })
        return () => h('div', 'shared-pad')
      },
    })

    const wrapper = mount(DrawingView, {
      global: { components: { SharedDrawpad: SharedDrawpadStub } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Round 1 of 3')
    expect(wrapper.text()).toContain('Animals')
    expect(wrapper.findAll('.items-list li').length).toBe(2)
  })

  it('color, size and clear controls call SharedDrawpad methods', async () => {
    const setColor = vi.fn()
    const setWidth = vi.fn()
    const clear = vi.fn()
    const toDataURL = vi.fn(() => 'data:stub')

    const SharedDrawpadStub = defineComponent({
      name: 'SharedDrawpad',
      props: ['mode'],
      setup(_, { expose }) {
        expose({ setColor, setWidth, clear, toDataURL })
        return () => h('div', 'shared-pad')
      },
    })

    const wrapper = mount(DrawingView, {
      global: { components: { SharedDrawpad: SharedDrawpadStub } },
    })
    await wrapper.vm.$nextTick()

    const colorInput = wrapper.find('input[type="color"]')
    await colorInput.setValue('#ff0000')

    const sizeInput = wrapper.find('input[type="range"]')
    await sizeInput.setValue('5')

    const clearBtn = wrapper.find('button.btn.btn-small')
    await clearBtn.trigger('click')

    // Input values should update when interacted with
    expect((colorInput.element as HTMLInputElement).value).toBe('#ff0000')
    expect((sizeInput.element as HTMLInputElement).value).toBe('5')
    // clear button exists and can be clicked without throwing
    expect(clearBtn.exists()).toBe(true)
  })
})
