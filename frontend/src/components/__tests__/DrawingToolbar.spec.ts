import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DrawingToolbar from "@/components/DrawingToolbar.vue";
import { i18n } from "@/i18n";

describe("DrawingToolbar", () => {
  it("labels a colour or brush size it has no name for with its value, never an empty button", () => {
    const w = mount(DrawingToolbar, {
      props: { currentColor: "#123456", currentWidth: 8, palette: ["#123456", "#2d2d2d"], sizes: [8, 3] },
      global: { plugins: [i18n] },
    });
    const labels = w.findAll("button.swatch, button.brush").map((b) => b.attributes("aria-label"));
    expect(labels).toEqual(["#123456", "Black", "8", "Small brush"]);
  });
});
