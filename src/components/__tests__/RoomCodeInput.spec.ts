import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import RoomCodeInput from '@/components/RoomCodeInput.vue'
import LobbyView from '@/views/LobbyView.vue'

// simple mocks and spies
const pushMock = vi.fn()
const connectMock = vi.fn()
const storeMock = {
  localPlayerName: '',
  setLocalPlayer: vi.fn(),
  setRoomCode: vi.fn(),
  setLocalPlayerAndSave: vi.fn(),
  setRoomCodeAndSave: vi.fn(),
}

vi.mock('vue-router', () => ({ useRouter: () => ({ push: pushMock }) }))
vi.mock('@/composables/useGameConnection', () => ({ useGameConnection: () => ({ connect: connectMock }) }))
vi.mock('@/stores/game', () => ({ useGameStore: () => storeMock }))

describe('Room code input (minimal)', () => {
  it('fills inputs on paste and uppercases typed letters', async () => {
    const wrapper = mount(RoomCodeInput, { props: { modelValue: '' } })
    const inputs = wrapper.findAll('input.code-input')
    expect(inputs).toHaveLength(6)

    const clipboard = new DataTransfer()
    clipboard.setData('text', ' ab 12c ')
    if (!inputs[0]) throw new Error('no first input')
    await inputs[0].trigger('paste', { clipboardData: clipboard })
    await wrapper.vm.$nextTick()

    const updates = wrapper.emitted('update:modelValue') || []
    expect(updates.length).toBeGreaterThan(0)
    const lastArr = updates[updates.length - 1]
    const last = lastArr ? (lastArr[0] as string) : ''
    // pasted cleaned string should be uppercased and whitespace removed
    expect(last).toBe('AB12C')

    // typing lowercase should result in uppercase in emitted model
    if (!inputs[1]) throw new Error('no second input')
    await inputs[1].setValue('x')
    await wrapper.vm.$nextTick()
    const updates2 = wrapper.emitted('update:modelValue') || []
    expect(updates2.length).toBeGreaterThan(0)
    const lastArr2 = updates2[updates2.length - 1]
    const last2 = lastArr2 ? (lastArr2[0] as string) : ''
    expect(last2[1]).toBe('X')
  })
})

describe('LobbyView (minimal)', () => {
  it('create room triggers navigation', async () => {
    const wrapper = mount(LobbyView)
    const nameInput = wrapper.find('#player-name')
    await nameInput.setValue('Test Player')
    const createBtn = wrapper.find('.btn.btn-primary')
    await createBtn.trigger('click')
    expect(pushMock).toHaveBeenCalled()
  })
})

describe('RoomCodeInput navigation and backspace', () => {
  it('handles typing, backspace clearing and arrow navigation', async () => {
    const wrapper = mount(RoomCodeInput, { props: { modelValue: '' } })
    const inputs = wrapper.findAll('input.code-input')
    expect(inputs).toHaveLength(6)

  // Type into first two inputs
  if (!inputs[0] || !inputs[1]) throw new Error('inputs missing')
  await inputs[0].setValue('a')
  await inputs[1].setValue('b')
  await wrapper.vm.$nextTick()
  const updates = wrapper.emitted('update:modelValue') || []
  expect(updates.length).toBeGreaterThan(0)
  const currentArr = updates[updates.length - 1]
  const current = currentArr ? (currentArr[0] as string) : ''
  expect(current.slice(0, 2)).toBe('AB')

    // Backspace on second input should clear it
  await inputs[1].trigger('keydown', { key: 'Backspace' })
  await wrapper.vm.$nextTick()
  const updates2 = wrapper.emitted('update:modelValue') || []
  expect(updates2.length).toBeGreaterThan(0)
  const currentArr2 = updates2[updates2.length - 1]
  const current2 = currentArr2 ? (currentArr2[0] as string) : ''
  expect(current2).toBe('A')

    // ArrowLeft and ArrowRight shouldn't throw and should focus appropriately
    await inputs[1].trigger('keydown', { key: 'ArrowLeft' })
    await inputs[0].trigger('keydown', { key: 'ArrowRight' })
  })
})
