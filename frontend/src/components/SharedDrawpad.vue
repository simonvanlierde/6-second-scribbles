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
// How many points of each stroke in the store are on the canvas, so a stroke that
// grows via delta fragments is rendered incrementally.
const drawnCounts = new Map<number, number>();
// The toolbar's clear empties only this pad: strokes before this store index stay
// off it, on redraws too, until the whole doodle is cleared.
let clearedBefore = 0;

// Pad coordinates (see PAD_SCALE) for the points drawn on this canvas, in pixels.
function toPad(points: Array<{ x: number; y: number }>): number[] {
  const { width, height } = canvas.size();
  // A pad out of the layout has no size, and its points have no position on it.
  if (width === 0 || height === 0) return [];
  const scale = (value: number, size: number) =>
    Math.min(PAD_SCALE, Math.max(0, Math.round((value / size) * PAD_SCALE)));
  return points.flatMap((p) => [scale(p.x, width), scale(p.y, height)]);
}

// A stored stroke from point `from` on, in this canvas's pixels.
function toCanvas(stroke: DrawStroke, from: number): CanvasStroke {
  const { width, height } = canvas.size();
  const points: Array<{ x: number; y: number }> = [];
  for (let i = from * 2; i + 1 < stroke.points.length; i += 2) {
    points.push({
      x: ((stroke.points[i] ?? 0) / PAD_SCALE) * width,
      y: ((stroke.points[i + 1] ?? 0) / PAD_SCALE) * height,
    });
  }
  return { color: stroke.color, width: stroke.width, points };
}

function redrawAll() {
  canvas.clear();
  drawnCounts.clear();
  store.currentStrokes.forEach((stroke, i) => {
    if (i >= clearedBefore) canvas.drawStroke(toCanvas(stroke, 0));
    drawnCounts.set(i, stroke.points.length / 2);
  });
}

function clearLocal() {
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

// Render incoming remote strokes incrementally: for each stroke, draw only the
// tail that hasn't been drawn yet.
watch(
  () => store.currentStrokes,
  (strokes) => {
    if (strokes.length === 0) {
      drawnCounts.clear();
      clearedBefore = 0;
      canvas.clear();
      return;
    }
    for (let i = 0; i < strokes.length; i++) {
      const stroke = strokes[i];
      if (!stroke) continue;
      const done = drawnCounts.get(i) ?? 0;
      const total = stroke.points.length / 2;
      if (total > done && i >= clearedBefore) {
        // Start one point back, so the new tail joins the part already drawn.
        canvas.drawStroke(toCanvas(stroke, Math.max(0, done - 1)));
        drawnCounts.set(i, total);
      }
    }
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
