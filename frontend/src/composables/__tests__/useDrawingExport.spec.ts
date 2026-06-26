import { afterEach, describe, expect, it, vi } from "vitest";

import { useDrawingExport } from "@/composables/useDrawingExport";

class FakeImage {
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  naturalWidth = 400;
  naturalHeight = 300;
  #src = "";
  set src(value: string) {
    this.#src = value;
    // Resolve asynchronously, like a real image load.
    queueMicrotask(() => this.onload?.());
  }
  get src() {
    return this.#src;
  }
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useDrawingExport", () => {
  it("composites a cream background under the drawing and downloads it", async () => {
    vi.stubGlobal("Image", FakeImage);

    const ctx = {
      fillStyle: "",
      fillRect: vi.fn(),
      drawImage: vi.fn(),
    };
    const canvas = {
      width: 0,
      height: 0,
      getContext: vi.fn(() => ctx),
      toDataURL: vi.fn(() => "data:image/png;base64,OUT"),
    };
    const anchor = { href: "", download: "", click: vi.fn() };

    const createElement = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "canvas") return canvas as unknown as HTMLCanvasElement;
      if (tag === "a") return anchor as unknown as HTMLAnchorElement;
      throw new Error(`unexpected element: ${tag}`);
    });

    await useDrawingExport().exportDrawing("data:image/png;base64,IN", "scribble-r2-alice.png");

    // Canvas sized to the source image.
    expect(canvas.width).toBe(400);
    expect(canvas.height).toBe(300);
    // Cream fill happens across the whole canvas, BEFORE the strokes are drawn.
    expect(ctx.fillStyle).toBe("#FDFBF7");
    expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, 400, 300);
    expect(ctx.fillRect.mock.invocationCallOrder[0]).toBeLessThan(ctx.drawImage.mock.invocationCallOrder[0]);
    // Downloads via an anchor with the requested filename.
    expect(anchor.href).toBe("data:image/png;base64,OUT");
    expect(anchor.download).toBe("scribble-r2-alice.png");
    expect(anchor.click).toHaveBeenCalledOnce();

    createElement.mockRestore();
  });
});
