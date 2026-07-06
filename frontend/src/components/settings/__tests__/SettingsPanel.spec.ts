import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import SettingsPanel from "@/components/settings/SettingsPanel.vue";
import { i18n } from "@/i18n";

vi.mock("@/composables/useLocaleAvailability", () => ({
  useLocaleAvailability: () => ({
    localeOptions: { value: [] },
    fetchLocaleAvailability: vi.fn(),
  }),
}));

function mountPanel(initialState: Record<string, unknown> = {}) {
  return mount(SettingsPanel, {
    props: { open: true },
    global: {
      plugins: [
        createTestingPinia({
          createSpy: vi.fn,
          initialState: {
            game: {
              localPlayerName: "",
              localPlayerColor: "var(--avatar-1)",
              ...initialState,
            },
          },
          stubActions: false,
        }),
        i18n,
      ],
    },
  });
}

describe("SettingsPanel", () => {
  it("shows the current player name in the name input", () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    // The aria-label resolves through i18n, which may render as a key in the
    // isolated test context — find the name input by reference to the avatar
    // picker it sits next to instead.
    const input = w.findAll("input[type='text']").find((i) => i.element.tagName === "INPUT");
    expect(input).toBeTruthy();
    expect((input?.element as HTMLInputElement).value).toBe("Simon");
  });

  it("renders three theme options in the appearance segmented control", () => {
    const w = mountPanel();
    const seg = w.find(".seg");
    expect(seg.exists()).toBe(true);
    expect(seg.findAll(".seg__btn")).toHaveLength(3);
  });

  it("reveals an avatar color picker with 6 swatches when the avatar is clicked", async () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    // The picker is collapsed by default; clicking the avatar button expands it.
    expect(w.find('[role="radiogroup"][aria-label="Avatar color"]').exists()).toBe(false);
    await w.find(".avatar-btn").trigger("click");
    const picker = w.find('[role="radiogroup"][aria-label="Avatar color"]');
    expect(picker.exists()).toBe(true);
    expect(picker.findAll("button")).toHaveLength(6);
  });

  it("renders a sound toggle", () => {
    const w = mountPanel();
    const soundToggle = w.find(".switch__input");
    expect(soundToggle.exists()).toBe(true);
    expect((soundToggle.element as HTMLInputElement).type).toBe("checkbox");
  });
});
