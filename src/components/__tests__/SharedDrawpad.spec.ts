import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

// Use relative import to avoid alias resolution issues in some test environments
import SharedDrawpad from '../../components/SharedDrawpad.vue'

describe('SharedDrawpad', () => {
  it('sets logical size dataset attributes and exposes API', async () => {
    const wrapper = mount(SharedDrawpad, {
      props: { mode: 'compact' },
      attachTo: document.body,
    })

    // Wait for mounted hook to run
    await wrapper.vm.$nextTick()

    const canvas = wrapper.find('canvas')
    expect(canvas.exists()).toBe(true)
    // dataset should have been set to compact preset (680x420)
    expect(canvas.element.dataset.logicalWidth).toBe('680')
    expect(canvas.element.dataset.logicalHeight).toBe('420')

    // Exposed methods should exist
    const vm = wrapper.vm as unknown as Record<string, unknown>
    expect(typeof vm['loadDrawing']).toBe('function')
    expect(typeof vm['toDataURL']).toBe('function')
    expect(typeof vm['clear']).toBe('function')
    expect(typeof vm['setColor']).toBe('function')
    expect(typeof vm['setWidth']).toBe('function')
  })
})
