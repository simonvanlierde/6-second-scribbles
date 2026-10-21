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
// How many points of each stroke in the store are on the canvas, so the watcher
// only redraws strokes that grew.
const drawnCounts = new Map<number, number>();
// Remote strokes still drawn as live, by index in the store, each with the timer
// that commits it once its player stops sending fragments.
const LIVE_TIMEOUT_MS = 300;
const liveTimers = new Map<number, ReturnType<typeof setTimeout>>();
// The toolbar's clear empties only this pad: strokes before this store index stay
// off it, on redraws too, until the whole doodle is cleared.
let clearedBefore = 0;

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
  drawnCounts.clear();
  store.currentStrokes.forEach((stroke, i) => {
    drawnCounts.set(i, stroke.points.length / 2);
  });
  canvas.replaceStrokes(
    store.currentStrokes.filter((_, i) => i >= clearedBefore && !liveTimers.has(i)).map((s) => toCanvas(s)),
  );
  for (const i of liveTimers.keys()) {
    const stroke = store.currentStrokes[i];
    if (stroke) canvas.setLiveStroke(i, toCanvas(stroke));
  }
}

function commitRemote(index: number) {
  clearTimeout(liveTimers.get(index));
  liveTimers.delete(index);
  const stroke = store.currentStrokes[index];
  if (stroke) canvas.commitStroke(toCanvas(stroke), index);
  else canvas.setLiveStroke(index, null);
}

function dropRemote() {
  for (const timer of liveTimers.values()) clearTimeout(timer);
  liveTimers.clear();
}

function clearLocal() {
  dropRemote();
  canvas.clear();
  clearedBefore = store.currentStrokes.length;
}

function flushPending() {
  const points = toPad(pendingPoints);
  if (points.length > 0 && pendingMeta && store.localPlayerId) {
    const stroke = { color: pendingMeta.color, width: pendingMeta.width, points };
    send({ type: "draw_stroke_partial", playerId: store.localPlayerId, stroke, strokeStart: pendingStart });
    // Keep our own strokes in the store with everyone else's, so a resize can redraw
    // the whole doodle; they are already on the canvas.
    const index = store.applyPartialStroke(store.localPlayerId, stroke, pendingStart);
    drawnCounts.set(index, (store.currentStrokes[index]?.points.length ?? 0) / 2);
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
  () => store.currentStrokes,
  (strokes) => {
    if (strokes.length === 0) {
      drawnCounts.clear();
      dropRemote();
      clearedBefore = 0;
      canvas.clear();
      return;
    }
    for (let i = 0; i < strokes.length; i++) {
      const stroke = strokes[i];
      if (!stroke) continue;
      const total = stroke.points.length / 2;
      if (total > (drawnCounts.get(i) ?? 0) && i >= clearedBefore) {
        drawnCounts.set(i, total);
        clearTimeout(liveTimers.get(i));
        liveTimers.set(
          i,
          setTimeout(() => commitRemote(i), LIVE_TIMEOUT_MS),
        );
        canvas.setLiveStroke(i, toCanvas(stroke));
      }
    }
    for (const i of [...liveTimers.keys()]) if (!store.isLatestStroke(i)) commitRemote(i);
  },
  { deep: true },
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
