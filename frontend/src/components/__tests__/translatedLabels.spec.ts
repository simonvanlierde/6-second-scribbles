// cspell:ignore Avatarfarbe Blau erhöhen Gelb Großer Grün Kleiner Koralle Lachen Lavendel Mittlerer Pfirsich Pinsel
// cspell:ignore Reaktionen Runden Schließen Schwarz verringern Weiß Zeichnung
import { render } from "@testing-library/svelte";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import DrawingToolbar from "@/components/DrawingToolbar.svelte";
import StepperInput from "@/components/StepperInput.svelte";
import AvatarColorPicker from "@/components/settings/AvatarColorPicker.svelte";
import SettingsPanel from "@/components/settings/SettingsPanel.svelte";
import HdReactionPad from "@/components/ui/HdReactionPad.svelte";
import { AVATAR_COLORS } from "@/composables/useAvatar";
import { BRUSH_SIZES, DRAW_PALETTE } from "@/config/drawing";
import { setLocale } from "@/i18n";

// Screen-reader names are text too: they must follow the player's language.
describe("accessible names in German", () => {
  beforeAll(async () => {
    await setLocale("de");
  });
  afterAll(async () => {
    await setLocale("en");
  });

  it("names the stepper buttons", () => {
    const w = render(StepperInput, { props: { modelValue: 5, label: "Runden", min: 1, max: 10 } });
    const labels = Array.from(w.container.querySelectorAll("button"), (b) => b.getAttribute("aria-label"));
    expect(labels).toEqual(["Runden verringern", "Runden erhöhen"]);
  });

  it("names pen colours and brush sizes instead of hex codes and numbers", () => {
    const w = render(DrawingToolbar, {
      props: { currentColor: DRAW_PALETTE[0], currentWidth: BRUSH_SIZES[0] },
    });
    const labels = Array.from(w.container.querySelectorAll("button.swatch, button.brush"), (b) =>
      b.getAttribute("aria-label"),
    );
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
    const w = render(HdReactionPad, { props: { name: "Ada" } });
    expect(w.container.querySelector("[role=group]")?.getAttribute("aria-label")).toBe("Reaktionen auf Adas Zeichnung");
    expect(w.container.querySelector("button")?.getAttribute("aria-label")).toBe("Lachen für Adas Zeichnung");
  });

  it("names the avatar colours", () => {
    const w = render(AvatarColorPicker, { props: { modelValue: AVATAR_COLORS[0], initial: "A" } });
    expect(w.container.querySelector("[role=radiogroup]")?.getAttribute("aria-label")).toBe("Avatarfarbe");
    expect(Array.from(w.container.querySelectorAll("button"), (b) => b.getAttribute("aria-label"))).toEqual([
      "Koralle",
      "Grün",
      "Blau",
      "Gelb",
      "Lavendel",
      "Pfirsich",
    ]);
  });

  it("names the settings close button", () => {
    const w = render(SettingsPanel, {});
    expect(w.container.querySelector("[data-testid=hd-dialog-close]")?.getAttribute("aria-label")).toBe("Schließen");
  });
});
