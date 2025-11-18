// Global test setup for Vitest
// - Install a Pinia instance for tests (so stores work outside components)
// - Provide a minimal DataTransfer polyfill for clipboard/paste tests
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, vi } from 'vitest'

// Activate a global Pinia instance for tests
setActivePinia(createPinia())

// Minimal DataTransfer polyfill for environments that lack it (happy-dom etc)
if (typeof (globalThis as { DataTransfer?: unknown }).DataTransfer === 'undefined') {
  class _DataTransfer {
    private _data = new Map<string, string>()
    setData(type: string, value: string) {
      this._data.set(type, value)
    }
    getData(type: string) {
      return this._data.get(type) || ''
    }
  }

  ;(globalThis as { DataTransfer?: unknown }).DataTransfer = _DataTransfer
}

// Mock `vue-router` for tests so components that import it don't require a
// fully configured router. The mock provides minimal implementations of
// RouterView, useRouter, useRoute, createRouter and createMemoryHistory.
// Using `vi.mock` ensures the module is replaced for all tests run by Vitest.
vi.mock('vue-router', async () => {
  const vue = await import('vue')
  return {
    __esModule: true,
    // A very small RouterView that renders its default slot when provided.
    // When mounted without a router (like in App.spec) we render a simple
    // placeholder so legacy tests that expect a minimal render continue to work.
    RouterView: vue.defineComponent({
      name: 'MockRouterView',
      setup(_, { slots }) {
        return () => (slots.default ? slots.default() : vue.h('div', 'You did it!'))
      },
    }),
    // Minimal composables expected by application code
    useRouter: () => ({ push: () => {}, currentRoute: { value: {} } }),
    useRoute: () => ({ params: {}, name: undefined }),
    // Provide a minimal RouterLink for template usage in tests
    RouterLink: vue.defineComponent({
      name: 'RouterLink',
      props: ['to'],
      setup(_, { slots }) {
        return () => (slots.default ? slots.default() : vue.h('a'))
      },
    }),
    // createRouter/createMemoryHistory fulfill API shape for tests that
    // construct a router but never use its internals.
    createRouter: () => ({ install: (_app: unknown) => {} }),
    createMemoryHistory: () => ({}),
  }
})

// Minimal HTMLCanvasElement polyfill for test environments that don't
// implement canvas 2D context methods (JSDOM prints noisy warnings).
// We provide a lightweight 2D context with no-op drawing methods and a
// simple toDataURL implementation so components and tests can call canvas
// APIs without throwing.
try {
  if (typeof HTMLCanvasElement !== 'undefined') {
    type CanvasProto = {
      getContext?: (type: string) => unknown
      toDataURL?: () => string
      [k: string]: unknown
    }

    const proto = HTMLCanvasElement.prototype as unknown as CanvasProto

    if (typeof proto.getContext !== 'function') {
      proto.getContext = function (_type: string) {
        // Minimal 2D context with commonly used no-op methods
        return {
          fillRect: () => {},
          clearRect: () => {},
          getImageData: (x: number, y: number, w: number, h: number) => ({
            data: new Uint8ClampedArray(w * h * 4),
            width: w,
            height: h,
          }),
          putImageData: () => {},
          createImageData: (w: number, h: number) => new Uint8ClampedArray(w * h * 4),
          setTransform: () => {},
          drawImage: () => {},
          save: () => {},
          restore: () => {},
          beginPath: () => {},
          moveTo: () => {},
          lineTo: () => {},
          bezierCurveTo: () => {},
          quadraticCurveTo: () => {},
          arc: () => {},
          fill: () => {},
          stroke: () => {},
          closePath: () => {},
          measureText: (s: string) => ({ width: String(s).length * 8 }),
          translate: () => {},
          scale: () => {},
          rotate: () => {},
        }
      }
    }

    if (typeof proto.toDataURL !== 'function') {
      proto.toDataURL = function () {
        return 'data:image/png;base64,'
      }
    }
  }
} catch {
  // ignore in environments where HTMLCanvasElement isn't available
}

// Track timers created during tests so we can clear them and avoid the test
// process hanging due to stray intervals/timeouts (e.g. heartbeats).
const _setInterval = globalThis.setInterval.bind(globalThis)
const _setTimeout = globalThis.setTimeout.bind(globalThis)
const _clearInterval = globalThis.clearInterval.bind(globalThis)
const _clearTimeout = globalThis.clearTimeout.bind(globalThis)

// Timers IDs in jsdom/node can be numbers or objects; use `unknown` and store generically
const _activeTimers = new Set<unknown>()

globalThis.setInterval = ((fn: TimerHandler, ms?: number, ...args: unknown[]) => {
  const id = _setInterval(fn, ms, ...args)
  _activeTimers.add(id)
  return id
}) as typeof globalThis.setInterval

globalThis.setTimeout = ((fn: TimerHandler, ms?: number, ...args: unknown[]) => {
  const id = _setTimeout(fn, ms, ...args)
  _activeTimers.add(id)
  return id
}) as typeof globalThis.setTimeout

/* eslint-disable @typescript-eslint/no-explicit-any */
globalThis.clearInterval = ((id?: unknown) => {
  if (id !== undefined) _activeTimers.delete(id)
  return _clearInterval(id as any)
}) as typeof globalThis.clearInterval

globalThis.clearTimeout = ((id?: unknown) => {
  if (id !== undefined) _activeTimers.delete(id)
  return _clearTimeout(id as any)
}) as typeof globalThis.clearTimeout
/* eslint-enable @typescript-eslint/no-explicit-any */

afterEach(() => {
  // Clear pending timers created during the test
  for (const id of Array.from(_activeTimers)) {
    /* eslint-disable @typescript-eslint/no-explicit-any */
    try {
      _clearInterval(id as any)
      _clearTimeout(id as any)
    } catch {
      // ignore errors while clearing timers (some timer ids may already be cleared)
    }
    /* eslint-enable @typescript-eslint/no-explicit-any */
    _activeTimers.delete(id)
  }
})
