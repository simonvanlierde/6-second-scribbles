import { describe, expect, it } from "vitest";

import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import type { DrawStroke } from "@/shared/types";

const stroke = (color: string): DrawStroke => ({ color, width: 5, points: [{ x: 0, y: 0 }] });

describe("useDrawingCanvas.undo", () => {
  it("removes the most recent stroke", () => {
    const canvas = useDrawingCanvas();
    canvas.replaceStrokes([stroke("#000"), stroke("#f00"), stroke("#00f")]);

    canvas.undo();

    expect(canvas.strokes.value.map((s) => s.color)).toEqual(["#000", "#f00"]);
  });

  it("is a no-op when there are no strokes", () => {
    const canvas = useDrawingCanvas();
    expect(() => canvas.undo()).not.toThrow();
    expect(canvas.strokes.value).toEqual([]);
  });
});
