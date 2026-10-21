<template>
  <div>
    <div class="mb-2">
      <DrawingToolbar
        :current-color="color"
        :current-width="width"
        :show-undo="false"
        compact
        @select-color="color = $event"
        @select-size="width = $event"
        @clear="clearLocal"
      />
    </div>
    <DrawingCanvasStage class="shared-drawpad__stage"><canvas ref="canvasEl" /></DrawingCanvasStage>
    <p class="mt-2 text-center text-sm text-ink-muted max-[768px]:text-xs">
      {{ $t("lobby.drawTogetherWhileWaiting") }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";

import DrawingCanvasStage from "@/components/DrawingCanvasStage.vue";
import DrawingToolbar from "@/components/DrawingToolbar.vue";
import { type CanvasStroke, useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { BRUSH_SIZES, DRAW_PALETTE, PAD_SCALE } from "@/config/drawing";
import type { DrawStroke } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const canvas = useDrawingCanvas();
const canvasEl = useTemplateRef<HTMLCanvasElement>("canvasEl");
const store = useGameStore();
const { send } = useGameConnection();

const color = ref<string>(DRAW_PALETTE[0]);
const width = ref<number>(BRUSH_SIZES[1]);

// Strokes go out at most this often: a send per animation frame (60 a second) made
// relay cost on the server grow with frame rate rather than with drawing.
const SEND_INTERVAL_MS = 50;
let sendTimer: ReturnType<typeof setTimeout> | null = null;
// Delta points buffered since the last send, so the socket carries only new points,
// not the whole growing stroke.
let pendingPoints: Array<{ x: number; y: number }> = [];
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
  const drawingLocal = canvas.isDrawing.value;
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
  const points = toPad(pendingPoints);
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
watch(
  () => store.strokesVersion,
  () => {
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
        // Its player has moved on (or it came in a room_state snapshot): fill it once,
        // not live, or a join with many strokes repaints them all on every one.
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
    // A live stroke whose player started another, or that the store dropped past its caps.
    const held = new Set(strokes);
    for (const stroke of [...liveTimers.keys()]) {
      if (!held.has(stroke)) {
        clearTimeout(liveTimers.get(stroke));
        liveTimers.delete(stroke);
        canvas.setLiveStroke(stroke, null);
      } else if (!store.isLatestStroke(stroke)) commitRemote(stroke);
    }
  },
);

watch(color, (v) => canvas.setColor(v));
watch(width, (v) => canvas.setWidth(v));

onMounted(() => {
  if (!canvasEl.value) return;

  canvas.setResizeHandler(redrawAll);
  canvas.initCanvas(canvasEl.value);
  canvas.setColor(color.value);
  canvas.setWidth(width.value);
  redrawAll();

  canvas.setStrokeProgressCallback((delta) => {
    if (delta.first) {
      // Send the previous stroke's buffered tail before starting a new one, so a
      // rapid up→down within one frame doesn't drop the old stroke's last points.
      flushPending();
      pendingStart = true;
    }
    pendingMeta = { color: delta.color, width: delta.width };
    pendingPoints.push(...delta.points);
    scheduleSend();
  });
});

// Send what is buffered while the pad is still laid out, so its points still scale.
onBeforeUnmount(() => {
  if (sendTimer !== null) clearTimeout(sendTimer);
  flushPending();
});

onUnmounted(() => {
  dropRemote();
  canvas.cleanup();
});
</script>

<style scoped>
.shared-drawpad__stage {
  height: 320px;
}
@media (max-width: 768px) {
  .shared-drawpad__stage {
    height: 220px;
  }
}
@media (max-width: 480px) {
  .shared-drawpad__stage {
    height: 180px;
  }
}
</style>
