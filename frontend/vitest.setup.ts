import { cleanup } from "@testing-library/svelte";
import { afterEach, beforeEach, vi } from "vitest";

if (typeof globalThis.DataTransfer === "undefined") {
  class MemoryDataTransfer {
    private data = new Map<string, string>();
    setData(type: string, value: string) {
      this.data.set(type, value);
    }
    getData(type: string) {
      return this.data.get(type) ?? "";
    }
  }
  Object.defineProperty(globalThis, "DataTransfer", { value: MemoryDataTransfer, configurable: true });
}

function createMemoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (key) => data.get(key) ?? null,
    key: (index) => [...data.keys()][index] ?? null,
    removeItem: (key) => {
      data.delete(key);
    },
    setItem: (key, value) => {
      data.set(key, String(value));
    },
  };
}

for (const name of ["localStorage", "sessionStorage"] as const) {
  const value = createMemoryStorage();
  Object.defineProperty(globalThis, name, { value, writable: true, configurable: true });
  Object.defineProperty(window, name, { value, writable: true, configurable: true });
}

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.useRealTimers();
  vi.restoreAllMocks();
});
afterEach(cleanup);

if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
    this.dispatchEvent(new Event("close"));
  };
}

if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: query.includes("prefers-reduced-motion"),
    media: query,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent: () => true,
  });
}
