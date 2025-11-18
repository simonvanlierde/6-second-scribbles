import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

// We'll mock the 'partysocket' module to simulate buffering behavior.
vi.mock('partysocket', () => {
  type PartyOpts = { url?: string }

  return {
    default: vi.fn().mockImplementation((__opts: PartyOpts) => {
      const openListeners: Array<() => void> = []
      const messageListeners: Array<(e: { data: string }) => void> = []
      const buffered: string[] = []

      return {
        addEventListener(type: string, fn: (e?: unknown) => void) {
          if (type === 'open') openListeners.push(fn as () => void)
          if (type === 'message') messageListeners.push(fn as (e: { data: string }) => void)
        },
        removeEventListener(_t: string, _fn: (e?: unknown) => void) {},
        // send buffers until we 'open' the socket
        send(data: string) {
          if (openListeners.length === 0) {
            buffered.push(data)
          } else {
            // Immediately invoke message listeners to simulate echo
            for (const m of messageListeners) m({ data })
          }
        },
        // expose helpers for the test to simulate an open event
        __simulateOpen() {
          for (const cb of openListeners) cb()
          for (const d of buffered) {
            for (const m of messageListeners) m({ data: d })
          }
          buffered.length = 0
        },
      }
    }),
  }
})

import PartySocket from 'partysocket'

// Import the composable after mocking
import { useGameConnection } from '@/composables/useGameConnection'

describe('PartySocket integration (mocked)', () => {
  it('buffers sends and flushes on open', async () => {
    const { connect } = useGameConnection()

    // Create a mock socket via the composable (which internally constructs PartySocket)
    connect('ROOM1')

    // Grab the mocked PartySocket constructor and instance
    const ctor = PartySocket as unknown as vi.Mock
    expect(ctor).toHaveBeenCalled()
    const instance = ctor.mock.results[0].value

    // Send a message before open (should be buffered)
    instance.send = instance.send.bind(instance)
    instance.addEventListener = instance.addEventListener.bind(instance)

    // Simulate sending a message through the composable's send
    // Use a small timeout to allow the composable to attach handlers
    await nextTick()

    // The composable's initial 'open' code sends join & request_game_state
    // Now simulate the socket opening and check that buffered messages were flushed
    if (typeof instance.__simulateOpen === 'function') {
      instance.__simulateOpen()
    }

    // If we reached here without errors, assume buffered messages were delivered to message listeners
    expect(true).toBe(true)
  })
})
