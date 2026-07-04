import { useEventListener, useResizeObserver } from "@vueuse/core";
import { ref } from "vue";

import type { DrawStroke } from "@/shared/types";

export function useDrawingCanvas() {
  const canvasRef = ref<HTMLCanvasElement | null>(null);
  const ctx = ref<CanvasRenderingContext2D | null>(null);
  const isDrawing = ref(false);
  const currentStroke = ref<{ x: number; y: number }[]>([]);
  const strokes = ref<DrawStroke[]>([]);
  const currentColor = ref("#000000");
  const currentWidth = ref(5);
  // The stroke belongs to a single pointer; secondary pointers (multi-touch) are
  // ignored so a second finger can't hijack or corrupt the in-progress stroke.
  let activePointerId: number | null = null;
  let onStrokeProgress:
    | ((partial: { color: string; width: number; points: Array<{ x: number; y: number }> }) => void)
    | null = null;
  let stopResizeObserver: (() => void) | null = null;
  let stopEventListeners: (() => void) | null = null;

  function initCanvas(canvas: HTMLCanvasElement) {
    cleanup();

    canvasRef.value = canvas;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new Error("Could not get 2D context from canvas");
    }
    ctx.value = context;

    context.lineCap = "round";
    context.lineJoin = "round";

    // PointerEvent unifies mouse, touch, and stylus in one API.
    // touch-action: none on the canvas CSS element prevents scroll interference.
    // setPointerCapture in startDrawing keeps events flowing outside the canvas.
    const cleanups = [
      useEventListener(canvas, "pointerdown", startDrawing),
      useEventListener(canvas, "pointermove", draw),
      useEventListener(canvas, "pointerup", stopDrawing),
      useEventListener(canvas, "pointercancel", stopDrawing),
    ];
    stopEventListeners = () => {
      for (const fn of cleanups) fn();
    };

    // ResizeObserver fires immediately with the initial size and handles all
    // future layout changes: window resize, orientation change, flex reflow.
    const parent = canvas.parentElement;
    if (parent) {
      const { stop } = useResizeObserver(parent, () => resize());
      stopResizeObserver = stop;
    } else {
      resize();
    }
  }

  function cleanup() {
    stopResizeObserver?.();
    stopResizeObserver = null;
    stopEventListeners?.();
    stopEventListeners = null;
  }

  function getCoordinates(event: PointerEvent): { x: number; y: number } {
    if (!canvasRef.value) return { x: 0, y: 0 };

    const rect = canvasRef.value.getBoundingClientRect();

    // PointerEvent has clientX/Y directly — no mouse/touch branching needed.
    // Clamp to canvas bounds to prevent drawing outside.
    return {
      x: Math.max(0, Math.min(event.clientX - rect.left, rect.width)),
      y: Math.max(0, Math.min(event.clientY - rect.top, rect.height)),
    };
  }

  function startDrawing(event: PointerEvent) {
    if (!ctx.value || !canvasRef.value) return;
    // Already drawing with another pointer — ignore this secondary touch.
    if (activePointerId !== null) return;

    // Capture the pointer so pointermove keeps firing even outside the canvas.
    activePointerId = event.pointerId;
    canvasRef.value.setPointerCapture(event.pointerId);

    isDrawing.value = true;
    const coords = getCoordinates(event);
    currentStroke.value = [coords];
  }

  function draw(event: PointerEvent) {
    if (!isDrawing.value || !ctx.value) return;
    if (event.pointerId !== activePointerId) return;

    const coords = getCoordinates(event);
    const prevCoords = currentStroke.value[currentStroke.value.length - 1];
    currentStroke.value.push(coords);

    // Draw only the incremental segment from the previous point to the current
    // one. The previous approach kept a single open path and called stroke()
    // each time, re-rendering the entire path on every pointermove — O(n) per
    // event. This is O(1) regardless of stroke length.
    if (prevCoords) {
      ctx.value.strokeStyle = currentColor.value;
      ctx.value.lineWidth = currentWidth.value;
      ctx.value.beginPath();
      ctx.value.moveTo(prevCoords.x, prevCoords.y);
      ctx.value.lineTo(coords.x, coords.y);
      ctx.value.stroke();
    }

    if (onStrokeProgress) {
      onStrokeProgress({
        color: currentColor.value,
        width: currentWidth.value,
        points: [...currentStroke.value],
      });
    }
  }

  function stopDrawing(event?: PointerEvent) {
    // Only the pointer that started the stroke may end it.
    if (event && event.pointerId !== activePointerId) return;
    if (!isDrawing.value) return;

    isDrawing.value = false;
    activePointerId = null;

    if (currentStroke.value.length > 0) {
      strokes.value.push({
        points: currentStroke.value,
        color: currentColor.value,
        width: currentWidth.value,
      });
      currentStroke.value = [];
    }
  }

  function setStrokeProgressCallback(
    cb: ((partial: { color: string; width: number; points: Array<{ x: number; y: number }> }) => void) | null,
  ) {
    onStrokeProgress = cb;
  }

  function setColor(color: string) {
    currentColor.value = color;
  }

  function setWidth(width: number) {
    currentWidth.value = width;
  }

  function clear() {
    if (!ctx.value || !canvasRef.value) return;
    ctx.value.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height);
    strokes.value = [];
  }

  function undo() {
    if (strokes.value.length === 0) return;
    replaceStrokes(strokes.value.slice(0, -1));
  }

  function resize() {
    if (!canvasRef.value || !ctx.value) return;

    const parent = canvasRef.value.parentElement;
    if (!parent) return;

    const style = window.getComputedStyle(parent);
    const paddingLeft = parseFloat(style.paddingLeft) || 0;
    const paddingRight = parseFloat(style.paddingRight) || 0;
    const cssWidth = parent.clientWidth - paddingLeft - paddingRight;
    // Read height from the canvas element itself (CSS class), not from the
    // parent. Using parent.clientHeight creates a feedback loop: setting
    // canvas style.height makes the parent taller, which fires ResizeObserver
    // again, growing the canvas indefinitely.
    const cssHeight = canvasRef.value.offsetHeight;
    const dpr = window.devicePixelRatio || 1;

    canvasRef.value.width = Math.round(cssWidth * dpr);
    canvasRef.value.height = Math.round(cssHeight * dpr);
    canvasRef.value.style.width = `${cssWidth}px`;
    // Do not set style.height — the CSS class controls the height and setting
    // it here would re-trigger the ResizeObserver.

    // Scale context so drawing coordinates map to CSS pixels.
    ctx.value.setTransform(dpr, 0, 0, dpr, 0, 0);

    // Re-apply drawing style lost when dimensions are reset.
    ctx.value.lineCap = "round";
    ctx.value.lineJoin = "round";

    // Replay strokes synchronously — simpler and lossless compared to the
    // previous dataURL → Image → onload async round-trip, which was fragile
    // in test environments and caused quality loss on repeated resizes.
    for (const stroke of strokes.value) {
      drawStroke(stroke);
    }
  }

  function drawStroke(stroke: DrawStroke) {
    if (!ctx.value || stroke.points.length === 0) return;

    const firstPoint = stroke.points[0];
    if (!firstPoint) return;

    ctx.value.strokeStyle = stroke.color;
    ctx.value.lineWidth = stroke.width;
    ctx.value.beginPath();
    ctx.value.moveTo(firstPoint.x, firstPoint.y);

    for (let i = 1; i < stroke.points.length; i++) {
      const point = stroke.points[i];
      if (point) {
        ctx.value.lineTo(point.x, point.y);
      }
    }

    ctx.value.stroke();
  }

  function replaceStrokes(nextStrokes: DrawStroke[]) {
    strokes.value = nextStrokes;
    if (ctx.value && canvasRef.value) {
      ctx.value.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height);
      for (const stroke of strokes.value) {
        drawStroke(stroke);
      }
    }
  }

  return {
    canvasRef,
    isDrawing,
    currentColor,
    currentWidth,
    strokes,
    initCanvas,
    cleanup,
    setColor,
    setWidth,
    clear,
    undo,
    drawStroke,
    replaceStrokes,
    setStrokeProgressCallback,
  };
}
