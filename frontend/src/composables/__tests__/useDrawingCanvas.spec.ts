import { beforeEach, describe, expect, it, vi } from "vitest";

import { type CanvasStroke, useDrawingCanvas } from "@/composables/useDrawingCanvas";

const stroke = (color: string): CanvasStroke => ({
  color,
  width: 5,
  points: [
    { x: 0, y: 0 },
    { x: 10, y: 10 },
  ],
});

// jsdom has no 2D context: give each canvas a fake that records the fill colours
// since its last clear, which is what that area of the canvas shows.
interface FakeContext {
  fills: string[];
  drawImages: number;
  cleared: number[];
}
const contexts = new Map<HTMLCanvasElement, FakeContext>();

function fakeContext(canvas: HTMLCanvasElement): FakeContext {
  const fake = {
    fills: [] as string[],
    drawImages: 0,
    cleared: [] as number[],
    fillStyle: "",
    clearRect: (...rect: number[]) => {
      fake.fills = [];
      fake.drawImages = 0;
      fake.cleared = rect;
    },
    fill: () => fake.fills.push(fake.fillStyle),
    drawImage: () => fake.drawImages++,
    save() {},
    restore() {},
    rect() {},
    clip() {},
    setTransform() {},
    beginPath() {},
    moveTo() {},
    quadraticCurveTo() {},
    closePath() {},
  };
  contexts.set(canvas, fake);
  return fake;
}

function mountCanvas() {
  const parent = document.createElement("div");
  const el = document.createElement("canvas");
  el.setPointerCapture = () => {};
  parent.appendChild(el);
  const canvas = useDrawingCanvas();
  canvas.initCanvas(el);
  const layer = [...contexts.entries()].find(([c]) => c !== el)?.[1];
  return { canvas, el, visible: contexts.get(el) as FakeContext, layer: layer as FakeContext };
}

// jsdom has no PointerEvent; the composable reads only pointerId and the client position.
function pointer(el: HTMLCanvasElement, type: string, x: number, y: number) {
  const event = new MouseEvent(type, { clientX: x, clientY: y });
  Object.defineProperty(event, "pointerId", { value: 1 });
  el.dispatchEvent(event);
}

beforeEach(() => {
  contexts.clear();
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function (this: HTMLCanvasElement) {
    return (contexts.get(this) ?? fakeContext(this)) as unknown as CanvasRenderingContext2D;
  } as unknown as typeof HTMLCanvasElement.prototype.getContext);
});

describe("useDrawingCanvas", () => {
  it("shows a stroke as live while drawing and commits it to the layer on pointerup", () => {
    const { canvas, el, visible, layer } = mountCanvas();
    canvas.setColor("#f00");

    pointer(el, "pointerdown", 0, 0);
    pointer(el, "pointermove", 0, 0);
    expect(layer.fills).toEqual([]);
    expect(visible.fills).toEqual(["#f00"]);

    pointer(el, "pointerup", 0, 0);
    expect(layer.fills).toEqual(["#f00"]);
    // The visible canvas now shows only the layer: no live stroke on top.
    expect(visible.fills).toEqual([]);
    expect(visible.drawImages).toBe(1);
    expect(canvas.strokes.value).toHaveLength(1);
  });

  it("commits a live stroke under its key and keeps other live strokes", () => {
    const { canvas, visible, layer } = mountCanvas();

    canvas.setLiveStroke("a", stroke("#0f0"));
    canvas.setLiveStroke("b", stroke("#00f"));
    expect(visible.fills).toEqual(["#0f0", "#00f"]);

    canvas.commitStroke(stroke("#0f0"), "a");
    expect(layer.fills).toEqual(["#0f0"]);
    expect(visible.fills).toEqual(["#00f"]);
  });

  it("undo redraws the layer without the last stroke and leaves live strokes", () => {
    const { canvas, visible, layer } = mountCanvas();
    canvas.replaceStrokes([stroke("#000"), stroke("#f00"), stroke("#00f")]);
    canvas.setLiveStroke("remote", stroke("#0f0"));

    canvas.undo();

    expect(canvas.strokes.value.map((s) => s.color)).toEqual(["#000", "#f00"]);
    expect(layer.fills).toEqual(["#000", "#f00"]);
    expect(visible.fills).toEqual(["#0f0"]);
  });

  it("repaints only around a live stroke, not the whole canvas", () => {
    const { canvas, el, visible } = mountCanvas();
    el.width = 1000;
    el.height = 1000;

    canvas.setLiveStroke("a", stroke("#0f0"));

    // The stroke spans 0-10 with a 5 px pen, so the area ends well inside 1000 px.
    const [x = -1, y = -1, w = 0, h = 0] = visible.cleared;
    expect([x, y]).toEqual([0, 0]);
    expect(w).toBeLessThan(30);
    expect(h).toBeLessThan(30);
    expect(visible.fills).toEqual(["#0f0"]);
  });

  it("moves the stroke being drawn with the pad when it resizes", () => {
    const observers: Array<() => void> = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(cb: () => void) {
          observers.push(cb);
        }
        observe() {}
        disconnect() {}
      },
    );
    const parent = document.createElement("div");
    const el = document.createElement("canvas");
    el.setPointerCapture = () => {};
    parent.appendChild(el);
    let size = { width: 200, height: 100 };
    Object.defineProperty(parent, "clientWidth", { get: () => size.width });
    Object.defineProperty(el, "offsetHeight", { get: () => size.height });
    el.getBoundingClientRect = () => ({ left: 0, top: 0, ...size }) as DOMRect;
    const canvas = useDrawingCanvas();
    canvas.initCanvas(el);
    observers[0]?.();

    pointer(el, "pointerdown", 100, 50);
    size = { width: 400, height: 200 };
    observers[0]?.();
    pointer(el, "pointerup", 0, 0);

    expect(canvas.strokes.value[0]?.points).toEqual([{ x: 200, y: 100 }]);
    vi.unstubAllGlobals();
  });

  it("undo is a no-op when there are no strokes", () => {
    const canvas = useDrawingCanvas();
    expect(() => canvas.undo()).not.toThrow();
    expect(canvas.strokes.value).toEqual([]);
  });
});
