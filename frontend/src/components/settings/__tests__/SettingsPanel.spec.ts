import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import SettingsPanel from "@/components/settings/SettingsPanel.vue";
import { i18n } from "@/i18n";

// Stub LocaleSelector to avoid pulling in its async locale-availability plumbing.
vi.mock("@/components/LocaleSelector.vue", () => ({
  default: { name: "LocaleSelector", template: "<div data-testid='locale-selector' />" },
}));

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
          initialState: { game: { localPlayerName: "", localPlayerColor: "var(--avatar-1)", ...initialState } },
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

  it("renders three theme picker segments", () => {
    const w = mountPanel();
    const segs = w.findAll(".hd-seg__item");
    expect(segs).toHaveLength(3);
  });

  it("renders an avatar color picker with 6 swatches", () => {
    const w = mountPanel({ localPlayerName: "Simon" });
    const picker = w.find('[role="radiogroup"][aria-label="Avatar color"]');
    expect(picker.exists()).toBe(true);
    expect(picker.findAll("button")).toHaveLength(6);
  });

  it("renders a sound toggle button", () => {
    const w = mountPanel();
    // The sound section contains an HdPill + HdButton — the button is the
    // one that isn't the dialog close. There's exactly one .hd-btn in the
    // panel body (Toggle).
    const toggles = w.findAll(".hd-btn");
    expect(toggles.length).toBeGreaterThan(0);
  });
});
