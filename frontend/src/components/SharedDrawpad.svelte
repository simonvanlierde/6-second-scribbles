<script lang="ts">
import { onDestroy, onMount, untrack } from "svelte";
import DrawingCanvasStage from "@/components/DrawingCanvasStage.svelte";
import DrawingToolbar from "@/components/DrawingToolbar.svelte";
import { type CanvasStroke, useDrawingCanvas } from "@/composables/useDrawingCanvas.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { BRUSH_SIZES, DRAW_PALETTE, PAD_SCALE } from "@/config/drawing";
import { t } from "@/i18n";
import type { DrawStroke } from "@/shared/types";
import { useGameStore } from "@/stores/game.svelte";

const canvas = useDrawingCanvas();
let canvasEl = $state<HTMLCanvasElement | null>(null);
const store = useGameStore();
const { send } = useGameConnection();

let color = $state<string>(DRAW_PALETTE[0]);
let width = $state<number>(BRUSH_SIZES[1]);

// Strokes go out at most this often: a send per animation frame (60 a second) made
// relay cost on the server grow with frame rate rather than with drawing.
const SEND_INTERVAL_MS = 50;
let sendTimer: ReturnType<typeof setTimeout> | null = null;
// Delta points buffered since the last send, so the socket carries only new points,
// not the whole growing stroke.
let pendingPoints: number[] = [];
let pendingMeta: { color: string; width: number } | null = null;
let pendingStart = false;
// Strokes are tracked by object, not by place in the store: the store drops the
// oldest strokes past the server's caps, which moves every index.
// How many points of each stroke are on the canvas, so the watcher only redraws
// strokes that grew.
let drawnCounts = new WeakMap<DrawStroke, number>();
// Remote strokes still drawn as live, each with the timer that commits it once its
// player stops sending fragments.
const LIVE_TIMEOUT_MS = 300;
const liveTimers = new Map<DrawStroke, ReturnType<typeof setTimeout>>();
// The toolbar's clear empties only this pad: the strokes it cleared stay off it,
// on redraws too, until the whole doodle is cleared.
let cleared = new WeakSet<DrawStroke>();
// This player's latest stroke. While it is being drawn the canvas shows it live, so
// a redraw must not also commit it.
let localStroke: DrawStroke | null = null;

// Pad coordinates (see PAD_SCALE) for the points drawn on this canvas, in pixels.
function toPad(points: Array<{ x: number; y: number }>): number[] {
  const pad = canvas.size();
  // A pad out of the layout has no size, and its points have no position on it.
  if (pad.width === 0 || pad.height === 0) return [];
  const scale = (value: number, size: number) =>
    Math.min(PAD_SCALE, Math.max(0, Math.round((value / size) * PAD_SCALE)));
  return points.flatMap((p) => [scale(p.x, pad.width), scale(p.y, pad.height)]);
}

// A stored stroke in this canvas's pixels.
function toCanvas(stroke: DrawStroke): CanvasStroke {
  const pad = canvas.size();
  const points: Array<{ x: number; y: number }> = [];
  for (let i = 0; i + 1 < stroke.points.length; i += 2) {
    points.push({
      x: ((stroke.points[i] ?? 0) / PAD_SCALE) * pad.width,
      y: ((stroke.points[i + 1] ?? 0) / PAD_SCALE) * pad.height,
    });
  }
  return { color: stroke.color, width: stroke.width, points };
}

function redrawAll() {
  drawnCounts = new WeakMap();
  for (const stroke of store.currentStrokes) drawnCounts.set(stroke, stroke.points.length / 2);
  const drawingLocal = canvas.isDrawing;
  canvas.replaceStrokes(
    store.currentStrokes
      .filter((s) => !cleared.has(s) && !liveTimers.has(s) && !(drawingLocal && s === localStroke))
      .map((s) => toCanvas(s)),
  );
  for (const stroke of liveTimers.keys()) canvas.setLiveStroke(stroke, toCanvas(stroke));
}

function commitRemote(stroke: DrawStroke) {
  clearTimeout(liveTimers.get(stroke));
  liveTimers.delete(stroke);
  canvas.commitStroke(toCanvas(stroke), stroke);
}

function dropRemote() {
  for (const timer of liveTimers.values()) clearTimeout(timer);
  liveTimers.clear();
}

function clearLocal() {
  dropRemote();
  canvas.clear();
  cleared = new WeakSet(store.currentStrokes);
}

function flushPending() {
  const points = pendingPoints;
  if (points.length > 0 && pendingMeta && store.localPlayerId) {
    const stroke = { color: pendingMeta.color, width: pendingMeta.width, points };
    send({ type: "draw_stroke_partial", playerId: store.localPlayerId, stroke, strokeStart: pendingStart });
    // Keep our own strokes in the store with everyone else's, so a resize can redraw
    // the whole doodle; they are already on the canvas.
    localStroke = store.applyPartialStroke(store.localPlayerId, stroke, pendingStart);
    drawnCounts.set(localStroke, localStroke.points.length / 2);
  }
  pendingPoints = [];
  pendingStart = false;
}

function scheduleSend() {
  if (sendTimer !== null) return;
  sendTimer = setTimeout(() => {
    sendTimer = null;
    flushPending();
  }, SEND_INTERVAL_MS);
}

// A remote stroke stays live, refilled on each fragment, until its player starts
// another stroke or stops sending; then it is filled once as finished.
let watchStarted0 = false;
$effect(() => {
  const value = store.strokesVersion;
  if (!watchStarted0) {
    watchStarted0 = true;
    return;
  }
  untrack(() => {
    const strokes = store.currentStrokes;
    if (strokes.length === 0) {
      drawnCounts = new WeakMap();
      dropRemote();
      cleared = new WeakSet();
      canvas.clear();
      return;
    }
    for (const stroke of strokes) {
      const total = stroke.points.length / 2;
      if (total > (drawnCounts.get(stroke) ?? 0) && !cleared.has(stroke)) {
        drawnCounts.set(stroke, total);
        clearTimeout(liveTimers.get(stroke));

        if (!store.isLatestStroke(stroke)) {
          liveTimers.delete(stroke);
          canvas.commitStroke(toCanvas(stroke), stroke);
          continue;
        }
        liveTimers.set(
          stroke,
          setTimeout(() => commitRemote(stroke), LIVE_TIMEOUT_MS),
        );
        canvas.setLiveStroke(stroke, toCanvas(stroke));
      }
    }

    const held = new Set(strokes);
    for (const stroke of [...liveTimers.keys()]) {
      if (!held.has(stroke)) {
        clearTimeout(liveTimers.get(stroke));
        liveTimers.delete(stroke);
        canvas.setLiveStroke(stroke, null);
      } else if (!store.isLatestStroke(stroke)) commitRemote(stroke);
    }
  });
});

let watchStarted1 = false;
$effect(() => {
  const value = color;
  if (!watchStarted1) {
    watchStarted1 = true;
    return;
  }
  untrack(() => canvas.setColor(value));
});
let watchStarted2 = false;
$effect(() => {
  const value = width;
  if (!watchStarted2) {
    watchStarted2 = true;
    return;
  }
  untrack(() => canvas.setWidth(value));
});

onMount(() => {
  if (!canvasEl) return;

  canvas.setResizeHandler(redrawAll);
  canvas.initCanvas(canvasEl);
  canvas.setColor(color);
  canvas.setWidth(width);
  redrawAll();

  canvas.setStrokeProgressCallback((delta) => {
    if (delta.first) {
      // Send the previous stroke's buffered tail before starting a new one, so a
      // rapid up→down within one frame doesn't drop the old stroke's last points.
      flushPending();
      pendingStart = true;
    }
    pendingMeta = { color: delta.color, width: delta.width };
    // Normalize while the canvas is laid out; teardown runs after it detaches.
    pendingPoints.push(...toPad(delta.points));
    scheduleSend();
  });
});

// Send what is buffered while the pad is still laid out, so its points still scale.
onDestroy(() => {
  if (sendTimer !== null) clearTimeout(sendTimer);
  flushPending();
});

onDestroy(() => {
  dropRemote();
  canvas.cleanup();
});
</script>

<div>
  <div class="mb-2">
    <DrawingToolbar
      currentColor={color}
      currentWidth={width}
      showUndo={false}
      compact
      onselectColor={(event) => {
        color = event;
      }}
      onselectSize={(event) => {
        width = event;
      }}
      onclear={clearLocal}
    ></DrawingToolbar>
  </div>
  <DrawingCanvasStage class="shared-drawpad__stage"><canvas bind:this={canvasEl}></canvas></DrawingCanvasStage>
  <p class="mt-2 text-center text-sm text-ink-muted max-[768px]:text-xs">
    {t("lobby.drawTogetherWhileWaiting")}
  </p>
</div>

<style>
:global(div.canvas-stage.shared-drawpad__stage) {
  height: 320px;
}
@media (max-width: 768px) {
  :global(div.canvas-stage.shared-drawpad__stage) {
    height: 220px;
  }
}
@media (max-width: 480px) {
  :global(div.canvas-stage.shared-drawpad__stage) {
    height: 180px;
  }
}
</style>
