import { afterEach, describe, expect, it, vi } from "vitest";

import { encodeDrawing, MAX_DRAWING_CHARS } from "@/lib/drawingImage";

type FakeCanvas = {
  width: number;
  height: number;
  ctx: { fillStyle: string; fillRect: ReturnType<typeof vi.fn>; drawImage: ReturnType<typeof vi.fn> };
  getContext: () => FakeCanvas["ctx"];
  toDataURL: ReturnType<typeof vi.fn>;
};

// encode(type, quality, width) returns the data URL a canvas of that width gives.
function stubCanvases(encode: (type: string, quality: number | undefined, width: number) => string): FakeCanvas[] {
  const made: FakeCanvas[] = [];
  vi.spyOn(document, "createElement").mockImplementation(() => {
    const canvas: FakeCanvas = {
      width: 0,
      height: 0,
      ctx: { fillStyle: "", fillRect: vi.fn(), drawImage: vi.fn() },
      getContext: () => canvas.ctx,
      toDataURL: vi.fn((type: string, quality?: number) => encode(type, quality, canvas.width)),
    };
    made.push(canvas);
    return canvas as unknown as HTMLElement;
  });
  return made;
}

const source = { width: 2048, height: 2100, toDataURL: vi.fn() } as unknown as HTMLCanvasElement;

afterEach(() => {
  vi.restoreAllMocks();
});

describe("encodeDrawing", () => {
  it("scales a HiDPI canvas to 1024 px and encodes WebP over the background", () => {
    const made = stubCanvases((type) => `data:${type};base64,small`);

    const result = encodeDrawing(source, "rgb(255, 255, 255)");

    expect(result).toBe("data:image/webp;base64,small");
    const [canvas] = made;
    expect(canvas?.height).toBe(1024);
    expect(canvas?.width).toBe(999);
    expect(canvas?.ctx.fillStyle).toBe("rgb(255, 255, 255)");
    expect(canvas?.ctx.fillRect.mock.invocationCallOrder[0]).toBeLessThan(
      canvas?.ctx.drawImage.mock.invocationCallOrder[0] ?? 0,
    );
  });

  it("steps down quality, then size, until the drawing fits", () => {
    // Pretend only a canvas at most 640 px wide at quality 0.5 fits.
    stubCanvases((type, quality, width) => {
      const fits = width <= 640 && quality === 0.5;
      return `data:${type};base64,${"x".repeat(fits ? 10 : MAX_DRAWING_CHARS)}`;
    });

    const result = encodeDrawing(source, "#fff");

    expect(result.length).toBeLessThanOrEqual(MAX_DRAWING_CHARS);
    expect(result.startsWith("data:image/webp")).toBe(true);
  });

  it("falls back to PNG where the browser cannot encode WebP", () => {
    stubCanvases(() => "data:image/png;base64,small");

    expect(encodeDrawing(source, "#fff")).toBe("data:image/png;base64,small");
  });

  it("returns the smallest attempt when nothing fits", () => {
    stubCanvases((type, _quality, width) => `data:${type};base64,${"x".repeat(MAX_DRAWING_CHARS + width)}`);

    const result = encodeDrawing(source, "#fff");

    expect(result.length).toBe("data:image/webp;base64,".length + MAX_DRAWING_CHARS + 374);
  });
});
