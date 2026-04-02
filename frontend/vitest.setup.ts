// NOTE: this file runs only in the Vitest context. The editor/TS server may
// not always resolve test-only modules; we keep imports and minimal shims
// here but avoid triple-slash directives which are discouraged.
// Global test setup for Vitest
// - Install a Pinia instance for tests (so stores work outside components)
// - Provide a minimal DataTransfer polyfill for clipboard/paste tests
import { createPinia, setActivePinia } from "pinia";
import { vi } from "vitest";

// Activate a global Pinia instance for tests
setActivePinia(createPinia());

// Minimal DataTransfer polyfill for environments that lack it (happy-dom etc)
if (typeof (globalThis as { DataTransfer?: unknown }).DataTransfer === "undefined") {
  class _DataTransfer {
    private _data = new Map<string, string>();
    setData(type: string, value: string) {
      this._data.set(type, value);
    }
    getData(type: string) {
      return this._data.get(type) || "";
    }
  }

  (globalThis as { DataTransfer?: unknown }).DataTransfer = _DataTransfer;
}

// Mock `vue-router` for tests so components that import it don't require a
// fully configured router. The mock provides minimal implementations of
// RouterView, useRouter, useRoute, createRouter and createMemoryHistory.
// Using `vi.mock` ensures the module is replaced for all tests run by Vitest.
vi.mock("vue-router", async () => {
  const vue = await import("vue");
  return {
    __esModule: true,
    // A very small RouterView that renders its default slot when provided.
    // When mounted without a router (like in App.spec) we render a simple
    // placeholder so legacy tests that expect a minimal render continue to work.
    RouterView: vue.defineComponent({
      name: "MockRouterView",
      setup(_, { slots }) {
        return () => (slots.default ? slots.default() : vue.h("div", "You did it!"));
      },
    }),
    // Minimal composables expected by application code
    useRouter: () => ({ push: () => {}, currentRoute: { value: {} } }),
    useRoute: () => ({ params: {}, name: undefined }),
    // createRouter/createMemoryHistory fulfill API shape for tests that
    // construct a router but never use its internals.
    createRouter: () => ({ install: (_app: unknown) => {} }),
    createMemoryHistory: () => ({}),
  };
});
