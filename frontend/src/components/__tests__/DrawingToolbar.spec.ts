import { render } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import DrawingToolbar from "@/components/DrawingToolbar.svelte";

describe("DrawingToolbar", () => {
  it("labels a colour or brush size it has no name for with its value, never an empty button", () => {
    const w = render(DrawingToolbar, {
      props: { currentColor: "#123456", currentWidth: 8, palette: ["#123456", "#2d2d2d"], sizes: [8, 3] },
    });
    const labels = Array.from(w.container.querySelectorAll("button.swatch, button.brush"), (b) =>
      b.getAttribute("aria-label"),
    );
    expect(labels).toEqual(["#123456", "Black", "8", "Small brush"]);
  });
});
