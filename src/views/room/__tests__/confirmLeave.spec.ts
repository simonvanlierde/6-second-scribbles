import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// Views under test
import DrawingView from '@/views/room/DrawingView.vue'
import FinalResultsView from '@/views/room/FinalResultsView.vue'
import GuessingView from '@/views/room/GuessingView.vue'
import RoundResultsView from '@/views/room/RoundResultsView.vue'
import WaitingRoomView from '@/views/room/WaitingRoomView.vue'

// Create a shared router mock with a replace spy
const replaceSpy = vi.fn()
vi.mock('vue-router', async () => {
  const actual = await vi.importActual<any>('vue-router')
  return {
    ...actual,
    useRouter: () => ({ replace: replaceSpy }),
    useRoute: () => ({ params: {} }),
  }
})

// Mock composables and store used by views
const disconnectSpy = vi.fn()
vi.mock('@/composables/useGameConnection', () => ({ useGameConnection: () => ({ disconnect: disconnectSpy, send: vi.fn() }) }))

const resetSpy = vi.fn()
const storeMock: any = {
  reset: resetSpy,
  // provide minimal props used by views
  localPlayerId: 'p1',
  playersList: [],
  getFinalScores: () => [],
}
vi.mock('@/stores/game', () => ({ useGameStore: () => storeMock }))

// Stub out ConfirmDialog to avoid modal complexity
vi.mock('@/components/ConfirmDialog.vue', () => ({
  default: {
    template: '<div />',
    props: ['modelValue', 'title', 'message'],
  },
}))

describe('confirmLeave behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('DrawingView confirmLeave navigates home and cleans up', async () => {
    const wrapper = mount(DrawingView, { global: { stubs: { GameDrawpad: true, 'font-awesome-icon': true } } })
    await wrapper.vm.$nextTick()
    // call confirmLeave if present
    ;(wrapper.vm as any).confirmLeave?.()
    // leave() is async and awaits router.replace; give microtasks a tick
    await Promise.resolve()

    expect(disconnectSpy).toHaveBeenCalled()
    expect(resetSpy).toHaveBeenCalled()
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })

  it('RoundResultsView leaveRoom/confirmLeave navigates home and cleans up', async () => {
    const wrapper = mount(RoundResultsView, { global: { stubs: { 'font-awesome-icon': true } } })
    await wrapper.vm.$nextTick()
    ;(wrapper.vm as any).leaveRoom?.()
    await Promise.resolve()

    expect(disconnectSpy).toHaveBeenCalled()
    expect(resetSpy).toHaveBeenCalled()
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })

  it('FinalResultsView confirmLeaveRoom navigates home and cleans up', async () => {
    const wrapper = mount(FinalResultsView, { global: { stubs: { 'font-awesome-icon': true } } })
    await wrapper.vm.$nextTick()
    ;(wrapper.vm as any).confirmLeaveRoom?.()
    await Promise.resolve()

    expect(disconnectSpy).toHaveBeenCalled()
    expect(resetSpy).toHaveBeenCalled()
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })

  it('WaitingRoomView confirmLeave navigates home and cleans up', async () => {
    const wrapper = mount(WaitingRoomView, { global: { stubs: { 'font-awesome-icon': true } } })
    await wrapper.vm.$nextTick()
    ;(wrapper.vm as any).confirmLeave?.()
    await Promise.resolve()

    expect(disconnectSpy).toHaveBeenCalled()
    expect(resetSpy).toHaveBeenCalled()
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })

  it('GuessingView confirmLeave navigates home and cleans up', async () => {
    const wrapper = mount(GuessingView, { global: { stubs: { 'font-awesome-icon': true } } })
    await wrapper.vm.$nextTick()
    ;(wrapper.vm as any).confirmLeave?.()
    await Promise.resolve()

    expect(disconnectSpy).toHaveBeenCalled()
    expect(resetSpy).toHaveBeenCalled()
    expect(replaceSpy).toHaveBeenCalledWith('/')
  })
})
