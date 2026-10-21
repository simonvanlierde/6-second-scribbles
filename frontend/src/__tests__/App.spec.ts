import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import App from "@/App.vue";
import { useAnnouncer } from "@/composables/useAnnouncer";
import { i18n } from "@/i18n";

describe("App", () => {
  it("reads announcements out through one polite live region", async () => {
    const w = mount(App, {
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn }), i18n],
        stubs: { RouterView: true, SettingsPanel: true },
      },
    });
    const region = w.get("[role=status][aria-atomic=true]");
    expect(region.text()).toBe("");

    useAnnouncer().announce("Round 2: guessing");
    await nextTick();
    await nextTick();

    expect(region.text()).toBe("Round 2: guessing");
  });
});
