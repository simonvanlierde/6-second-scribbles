// cspell:ignore Avatarfarbe Blau erhöhen Gelb Großer Grün Kleiner Koralle Lachen Lavendel Mittlerer Pfirsich Pinsel
// cspell:ignore Reaktionen Runden Schließen Schwarz verringern Weiß Zeichnung
import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import DrawingToolbar from "@/components/DrawingToolbar.vue";
import StepperInput from "@/components/StepperInput.vue";
import AvatarColorPicker from "@/components/settings/AvatarColorPicker.vue";
import SettingsPanel from "@/components/settings/SettingsPanel.vue";
import HdReactionPad from "@/components/ui/HdReactionPad.vue";
import { AVATAR_COLORS } from "@/composables/useAvatar";
import { BRUSH_SIZES, DRAW_PALETTE } from "@/config/drawing";
import { i18n, setLocale } from "@/i18n";

// Screen-reader names are text too: they must follow the player's language.
describe("accessible names in German", () => {
  beforeAll(async () => {
    await setLocale("de");
  });
  afterAll(async () => {
    await setLocale("en");
  });

  const global = { plugins: [i18n] };

  it("names the stepper buttons", () => {
    const w = mount(StepperInput, { props: { modelValue: 5, label: "Runden", min: 1, max: 10 }, global });
    const labels = w.findAll("button").map((b) => b.attributes("aria-label"));
    expect(labels).toEqual(["Runden verringern", "Runden erhöhen"]);
  });

  it("names pen colours and brush sizes instead of hex codes and numbers", () => {
    const w = mount(DrawingToolbar, {
      props: { currentColor: DRAW_PALETTE[0], currentWidth: BRUSH_SIZES[0] },
      global,
    });
    const labels = w.findAll("button.swatch, button.brush").map((b) => b.attributes("aria-label"));
    expect(labels).toEqual([
      "Schwarz",
      "Weiß",
      "Rot",
      "Blau",
      "Grün",
      "Orange",
      "Kleiner Pinsel",
      "Mittlerer Pinsel",
      "Großer Pinsel",
    ]);
  });

  it("says whose drawing a reaction is for", () => {
    const w = mount(HdReactionPad, { props: { name: "Ada" }, global });
    expect(w.get("[role=group]").attributes("aria-label")).toBe("Reaktionen auf Adas Zeichnung");
    expect(w.get("button").attributes("aria-label")).toBe("Lachen für Adas Zeichnung");
  });

  it("names the avatar colours", () => {
    const w = mount(AvatarColorPicker, { props: { modelValue: AVATAR_COLORS[0], initial: "A" }, global });
    expect(w.get("[role=radiogroup]").attributes("aria-label")).toBe("Avatarfarbe");
    expect(w.findAll("button").map((b) => b.attributes("aria-label"))).toEqual([
      "Koralle",
      "Grün",
      "Blau",
      "Gelb",
      "Lavendel",
      "Pfirsich",
    ]);
  });

  it("names the settings close button", () => {
    const w = mount(SettingsPanel, {
      global: { plugins: [createTestingPinia({ createSpy: vi.fn, stubActions: false }), i18n] },
    });
    expect(w.get("[data-testid=hd-dialog-close]").attributes("aria-label")).toBe("Schließen");
  });
});
