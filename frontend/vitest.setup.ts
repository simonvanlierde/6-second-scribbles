// NOTE: this file runs only in the Vitest context. The editor/TS server may
// not always resolve test-only modules; we keep imports and minimal shims
// here but avoid triple-slash directives which are discouraged.
// Global test setup for Vitest
// - Install a Pinia instance for tests (so stores work outside components)
// - Provide a minimal DataTransfer polyfill for clipboard/paste tests

import { config } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { vi } from "vitest";
import en from "./src/locales/en.json";

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

// Web Storage polyfill. Node 26 exposes a native experimental `localStorage`
// global that is `undefined` (and warns) unless started with --localstorage-file,
// and it shadows the Storage jsdom would otherwise provide — so both
// `localStorage` and `sessionStorage` are unusable in tests. Install a plain
// in-memory Storage (theme, sound, and Pinia persistence all read it). The
// per-test `localStorage.clear()` below keeps it isolated between tests.
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key: string) => (store.has(key) ? (store.get(key) as string) : null),
    key: (index: number) => [...store.keys()][index] ?? null,
    removeItem: (key: string) => void store.delete(key),
    setItem: (key: string, value: string) => void store.set(key, String(value)),
  } as Storage;
}

for (const name of ["localStorage", "sessionStorage"] as const) {
  const value = createMemoryStorage();
  Object.defineProperty(globalThis, name, {
    value,
    writable: true,
    configurable: true,
  });
  if (typeof window !== "undefined") {
    Object.defineProperty(window, name, {
      value,
      writable: true,
      configurable: true,
    });
  }
}

// Global baseline mock for vue-router. Test files that need custom router
// behaviour (e.g. to capture push() calls) override this with their own
// vi.mock("vue-router", ...) — per-file mocks completely replace this one
// for that file. Files that don't override it (e.g. useGameConnection.spec)
// rely on these stubs so that useRouter()/useRoute() calls don't throw.
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

// Provide a minimal `$t` mock for components that use vue-i18n in templates.
// Some tests render components without installing the full i18n plugin,
// so stubbing `$t` keeps those renders quiet and deterministic.
// A small `$t` implementation for tests that looks up messages from the
// English locale and performs simple `{key}` interpolation when an object
// of values is passed as the second argument.
function lookupMessage(key: string) {
  const parts = key.split(".");
  let cur: unknown = en;
  for (const p of parts) {
    if (cur && typeof cur === "object" && p in (cur as Record<string, unknown>)) {
      cur = (cur as Record<string, unknown>)[p];
    } else return key;
  }
  return typeof cur === "string" ? cur : key;
}

config.global.mocks = {
  $t: (key: string, values?: Record<string, string> | string) => {
    let msg = lookupMessage(key);
    if (values && typeof values === "object") {
      for (const [k, v] of Object.entries(values)) {
        msg = msg.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      }
    }
    return msg;
  },
};

// Clear localStorage before each test to avoid leaking persisted state.
import { beforeEach as vitestBeforeEach } from "vitest";

vitestBeforeEach(() => {
  try {
    localStorage.clear();
  } catch {
    /* ignore environments without localStorage */
  }

  try {
    // Ensure tests use real timers by default (some specs switch to fake
    // timers and may not always restore them). This makes promise timing
    // behavior consistent across the suite.
    vi.useRealTimers();
  } catch {
    /* ignore if unavailable */
  }

  try {
    vi.restoreAllMocks();
  } catch {
    /* ignore if unavailable */
  }
});

// Stub transitions so content inside <Transition> is rendered immediately
// (avoids timing/flakiness in tests that assert on transient UI like toasts).
config.global.stubs = {
  Transition: { template: "<div><slot /></div>" },
};
