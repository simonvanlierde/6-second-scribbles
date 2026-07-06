import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { defineComponent, h } from "vue";

import { useRoundDraft } from "@/composables/useRoundDraft";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (k: string) => values.get(k) ?? null,
    key: (i: number) => Array.from(values.keys())[i] ?? null,
    removeItem: (k: string) => values.delete(k),
    setItem: (k: string, v: string) => values.set(k, v),
  };
}

const KEY = "draftKey";

type DraftApi = ReturnType<typeof useRoundDraft<string[]>>;

const wrappers: VueWrapper[] = [];

function mountDraft(opts: {
  round: () => number;
  apply: (d: string[]) => void;
  collect: () => string[];
  active: () => boolean;
}) {
  let api!: DraftApi;
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useRoundDraft<string[]>(KEY, opts);
        return () => h("div");
      },
    }),
  );
  wrappers.push(wrapper);
  return { wrapper, api };
}

beforeEach(() => {
  Object.defineProperty(globalThis, "localStorage", {
    value: createMemoryStorage(),
    configurable: true,
    writable: true,
  });
});

// Unmount between tests so leaked pagehide listeners don't fire across cases.
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
});

describe("useRoundDraft", () => {
  it("restores a draft saved for the current round", () => {
    localStorage.setItem(KEY, JSON.stringify({ round: 2, data: ["cat"] }));
    let applied: string[] | null = null;
    const { api } = mountDraft({
      round: () => 2,
      apply: (d) => {
        applied = d;
      },
      collect: () => [],
      active: () => true,
    });

    expect(api.restore()).toBe(true);
    expect(applied).toEqual(["cat"]);
  });

  it("discards (and removes) a draft from a different round", () => {
    localStorage.setItem(KEY, JSON.stringify({ round: 1, data: ["cat"] }));
    const { api } = mountDraft({
      round: () => 2,
      apply: () => {
        throw new Error("should not apply");
      },
      collect: () => [],
      active: () => true,
    });

    expect(api.restore()).toBe(false);
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  it("persists on pagehide only while active, and clear() removes it", () => {
    let active = true;
    const { api } = mountDraft({
      round: () => 3,
      apply: () => {},
      collect: () => ["dog"],
      active: () => active,
    });

    window.dispatchEvent(new Event("pagehide"));
    expect(JSON.parse(localStorage.getItem(KEY) ?? "{}")).toEqual({
      round: 3,
      data: ["dog"],
    });

    api.clear();
    expect(localStorage.getItem(KEY)).toBeNull();

    active = false;
    window.dispatchEvent(new Event("pagehide"));
    expect(localStorage.getItem(KEY)).toBeNull();
  });
});
