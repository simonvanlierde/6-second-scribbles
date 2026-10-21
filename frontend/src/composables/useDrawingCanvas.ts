import { getStroke, type StrokeOptions } from "perfect-freehand";
import { ref } from "vue";

/** A stroke in this canvas's CSS pixels. */
export interface CanvasStroke {
  color: string;
  width: number;
  points: Array<{ x: number; y: number }>;
}

// Tuned on a 360x180 pad at 3x density: a higher streamline cuts the tops off loops.
const STROKE_OPTIONS: StrokeOptions = { thinning: 0.5, smoothing: 0.5, streamline: 0.2, simulatePressure: true };
// The pen widths were picked for 2D-context lines; an outline of the same size looks thinner.
const SIZE_FACTOR = 1.3;
const LOCAL_STROKE = Symbol("local stroke");

/** An area of the canvas in CSS pixels. */
interface Rect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

function union(rects: Array<Rect | null>): Rect | null {
  let out: Rect | null = null;
  for (const r of rects) {
    if (!r) continue;
    out = out
      ? {
          x0: Math.min(out.x0, r.x0),
          y0: Math.min(out.y0, r.y0),
          x1: Math.max(out.x1, r.x1),
          y1: Math.max(out.y1, r.y1),
        }
      : r;
  }
  return out;
}

/** The area a stroke's outline can cover: its points plus the pen size around them. */
function bounds(stroke: CanvasStroke): Rect | null {
  const pad = stroke.width * SIZE_FACTOR + 2;
  let rect: Rect | null = null;
  for (const { x, y } of stroke.points) rect = union([rect, { x0: x - pad, y0: y - pad, x1: x + pad, y1: y + pad }]);
  return rect;
}

/**
 * Fill a stroke's outline. `last` marks it finished: without it perfect-freehand
 * leaves the tail off, because the pointer may still move.
 */
function fillStroke(context: CanvasRenderingContext2D, stroke: CanvasStroke, last: boolean) {
  const outline = getStroke(stroke.points, { ...STROKE_OPTIONS, size: stroke.width * SIZE_FACTOR, last });
  const first = outline[0];
  if (!first) return;
  context.fillStyle = stroke.color;
  context.beginPath();
  context.moveTo(first[0], first[1]);
  // Curve through the midpoints of the outline, as perfect-freehand's own SVG path does.
  for (let i = 0; i < outline.length; i++) {
    const [x0, y0] = outline[i] as [number, number];
    const [x1, y1] = outline[(i + 1) % outline.length] as [number, number];
    context.quadraticCurveTo(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2);
  }
  context.closePath();
  context.fill();
}

export function useDrawingCanvas() {
  const canvasRef = ref<HTMLCanvasElement | null>(null);
  const ctx = ref<CanvasRenderingContext2D | null>(null);
  const isDrawing = ref(false);
  const strokes = ref<CanvasStroke[]>([]);
  const currentColor = ref("#000000");
  const currentWidth = ref(5);
  // Finished strokes are filled once onto this hidden canvas. The visible canvas is
  // this layer plus every live stroke, refilled on each change, so it is always
  // current when the drawing is encoded.
  const layer = document.createElement("canvas");
  const layerCtx = layer.getContext("2d");
  // Strokes still growing: the local pointer's, and remote ones the caller feeds in.
  const liveStrokes = new Map<unknown, CanvasStroke>();
  // Where the live strokes were last painted, so the next render repaints only around
  // them: repainting the whole HiDPI canvas on every pointermove made the browser
  // redraw all of it each frame.
  let paintedLive: Rect | null = null;
  // Device pixels per CSS pixel, set on resize.
  let scale = 1;
  // The stroke belongs to a single pointer; secondary pointers (multi-touch) are
  // ignored so a second finger can't hijack or corrupt the in-progress stroke.
  let activePointerId: number | null = null;
  // Plain, not a ref: perfect-freehand reads every point on each pointermove.
  let currentStroke: Array<{ x: number; y: number }> = [];
  // Points already handed to onStrokeProgress, so each callback carries only the
  // newly added points (a delta) rather than the whole growing stroke.
  let progressEmittedCount = 0;
  let onStrokeProgress:
    | ((delta: { color: string; width: number; points: Array<{ x: number; y: number }>; first: boolean }) => void)
    | null = null;
  // Runs after a resize instead of replaying `strokes`, for a caller that keeps its
  // own strokes and redraws them at the new size.
  let onResize: (() => void) | null = null;
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

    // PointerEvent unifies mouse, touch, and stylus in one API.
    // touch-action: none on the canvas CSS element prevents scroll interference.
    // setPointerCapture in startDrawing keeps events flowing outside the canvas.
    const listeners = [
      ["pointerdown", startDrawing],
      ["pointermove", draw],
      ["pointerup", stopDrawing],
      ["pointercancel", stopDrawing],
    ] as const;
    for (const [type, listener] of listeners) canvas.addEventListener(type, listener);
    stopEventListeners = () => {
      for (const [type, listener] of listeners) canvas.removeEventListener(type, listener);
    };

    // ResizeObserver fires immediately with the initial size and handles all
    // future layout changes: window resize, orientation change, flex reflow.
    const parent = canvas.parentElement;
    if (parent) {
      const observer = new ResizeObserver(() => resize());
      observer.observe(parent);
      stopResizeObserver = () => observer.disconnect();
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

  /**
   * Repaint the visible canvas, the finished strokes with the live ones on top: all of
   * it, or only where the live strokes were and are now, plus `changed`.
   */
  function render(changed: Rect | "all" | null = null) {
    const context = ctx.value;
    const canvas = canvasRef.value;
    if (!context || !canvas) return;
    const live = [...liveStrokes.values()];
    const nextLive = union(live.map(bounds));
    const area = changed === "all" ? null : union([paintedLive, nextLive, changed]);
    paintedLive = nextLive;
    if (changed !== "all" && !area) return;

    context.save();
    context.setTransform(1, 0, 0, 1, 0, 0);
    // The repainted area in whole device pixels, inside the canvas.
    const x = area ? Math.max(0, Math.floor(area.x0 * scale)) : 0;
    const y = area ? Math.max(0, Math.floor(area.y0 * scale)) : 0;
    const w = (area ? Math.min(canvas.width, Math.ceil(area.x1 * scale)) : canvas.width) - x;
    const h = (area ? Math.min(canvas.height, Math.ceil(area.y1 * scale)) : canvas.height) - y;
    if (w > 0 && h > 0) {
      context.beginPath();
      context.rect(x, y, w, h);
      context.clip();
      context.clearRect(x, y, w, h);
      if (layer.width > 0 && layer.height > 0) context.drawImage(layer, x, y, w, h, x, y, w, h);
      context.setTransform(scale, 0, 0, scale, 0, 0);
      for (const stroke of live) fillStroke(context, stroke, false);
    }
    context.restore();
  }

  function liveStroke(): CanvasStroke {
    return { color: currentColor.value, width: currentWidth.value, points: currentStroke };
  }

  function startDrawing(event: PointerEvent) {
    if (!ctx.value || !canvasRef.value) return;
    // Already drawing with another pointer — ignore this secondary touch.
    if (activePointerId !== null) return;

    // Capture the pointer so pointermove keeps firing even outside the canvas.
    activePointerId = event.pointerId;
    canvasRef.value.setPointerCapture(event.pointerId);

    isDrawing.value = true;
    progressEmittedCount = 0;
    const coords = getCoordinates(event);
    currentStroke = [coords];
    setLiveStroke(LOCAL_STROKE, liveStroke());
  }

  function draw(event: PointerEvent) {
    if (!isDrawing.value || !ctx.value) return;
    if (event.pointerId !== activePointerId) return;

    currentStroke.push(getCoordinates(event));
    setLiveStroke(LOCAL_STROKE, liveStroke());

    if (onStrokeProgress) {
      // Emit only the points added since the last callback (delta), flagging the
      // first fragment of the stroke so receivers start a fresh stroke.
      const newPoints = currentStroke.slice(progressEmittedCount);
      if (newPoints.length > 0) {
        onStrokeProgress({
          color: currentColor.value,
          width: currentWidth.value,
          points: newPoints,
          first: progressEmittedCount === 0,
        });
        progressEmittedCount = currentStroke.length;
      }
    }
  }

  function stopDrawing(event?: PointerEvent) {
    // Only the pointer that started the stroke may end it.
    if (event && event.pointerId !== activePointerId) return;
    if (!isDrawing.value) return;

    isDrawing.value = false;
    activePointerId = null;

    if (currentStroke.length > 0) {
      const stroke = liveStroke();
      strokes.value.push(stroke);
      commitStroke(stroke, LOCAL_STROKE);
      currentStroke = [];
    }
  }

  function setStrokeProgressCallback(
    cb:
      | ((delta: { color: string; width: number; points: Array<{ x: number; y: number }>; first: boolean }) => void)
      | null,
  ) {
    onStrokeProgress = cb;
  }

  function setColor(color: string) {
    currentColor.value = color;
  }

  function setWidth(width: number) {
    currentWidth.value = width;
  }

  /** Show `stroke` as still growing under `key`, or drop it with null. */
  function setLiveStroke(key: unknown, stroke: CanvasStroke | null) {
    if (stroke) liveStrokes.set(key, stroke);
    else liveStrokes.delete(key);
    render();
  }

  /** Add a finished stroke to the drawing, replacing the live stroke under `key` if given. */
  function commitStroke(stroke: CanvasStroke, key?: unknown) {
    if (key !== undefined) liveStrokes.delete(key);
    if (layerCtx) fillStroke(layerCtx, stroke, true);
    render(bounds(stroke));
  }

  function clear() {
    strokes.value = [];
    liveStrokes.clear();
    layerCtx?.clearRect(0, 0, layer.width, layer.height);
    render("all");
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
    scale = dpr;

    canvasRef.value.width = layer.width = Math.round(cssWidth * dpr);
    canvasRef.value.height = layer.height = Math.round(cssHeight * dpr);
    canvasRef.value.style.width = `${cssWidth}px`;
    // Do not set style.height — the CSS class controls the height and setting
    // it here would re-trigger the ResizeObserver.

    // Scale both contexts so drawing coordinates map to CSS pixels.
    ctx.value.setTransform(dpr, 0, 0, dpr, 0, 0);
    layerCtx?.setTransform(dpr, 0, 0, dpr, 0, 0);

    if (onResize) {
      onResize();
      return;
    }
    replaceStrokes(strokes.value);
  }

  function setResizeHandler(cb: (() => void) | null) {
    onResize = cb;
  }

  /** The canvas size in CSS pixels. */
  function size(): { width: number; height: number } {
    const rect = canvasRef.value?.getBoundingClientRect();
    return { width: rect?.width ?? 0, height: rect?.height ?? 0 };
  }

  /** Redraw the finished strokes from scratch; live strokes stay. */
  function replaceStrokes(nextStrokes: CanvasStroke[]) {
    strokes.value = nextStrokes;
    if (layerCtx) {
      layerCtx.clearRect(0, 0, layer.width, layer.height);
      for (const stroke of nextStrokes) fillStroke(layerCtx, stroke, true);
    }
    render("all");
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
    commitStroke,
    setLiveStroke,
    replaceStrokes,
    setResizeHandler,
    setStrokeProgressCallback,
    size,
  };
}
