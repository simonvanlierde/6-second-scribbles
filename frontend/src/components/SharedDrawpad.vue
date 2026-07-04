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
import { onMounted, onUnmounted, ref, useTemplateRef, watch } from "vue";

import DrawingCanvasStage from "@/components/DrawingCanvasStage.vue";
import DrawingToolbar from "@/components/DrawingToolbar.vue";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { BRUSH_SIZES, DRAW_PALETTE } from "@/config/drawing";
import { useGameStore } from "@/stores/game";

const canvas = useDrawingCanvas();
const canvasEl = useTemplateRef<HTMLCanvasElement>("canvasEl");
const store = useGameStore();
const { send } = useGameConnection();

const color = ref<string>(DRAW_PALETTE[0]);
const width = ref<number>(BRUSH_SIZES[1]);

let rafId: number | null = null;
// Delta points buffered since the last send; flushed once per animation frame so
// the socket carries only new points, not the whole growing stroke.
let pendingPoints: Array<{ x: number; y: number }> = [];
let pendingMeta: { color: string; width: number } | null = null;
let pendingStart = false;
// How many points of each remote stroke we've already drawn, so a stroke that
// grows via delta fragments is rendered incrementally.
const drawnCounts = new Map<number, number>();

function clearLocal() {
  canvas.clear();
}

function scheduleSend() {
  if (rafId !== null) return;
  rafId = requestAnimationFrame(() => {
    rafId = null;
    if (pendingPoints.length > 0 && pendingMeta && store.localPlayerId) {
      send({
        type: "draw_stroke_partial",
        playerId: store.localPlayerId,
        stroke: { color: pendingMeta.color, width: pendingMeta.width, points: pendingPoints },
        strokeStart: pendingStart,
      });
      pendingPoints = [];
      pendingStart = false;
    }
  });
}

// Render incoming remote strokes incrementally: for each stroke, draw only the
// tail that hasn't been drawn yet.
watch(
  () => store.currentStrokes,
  (strokes) => {
    if (strokes.length === 0) {
      drawnCounts.clear();
      canvas.clear();
      return;
    }
    for (let i = 0; i < strokes.length; i++) {
      const stroke = strokes[i];
      if (!stroke) continue;
      const done = drawnCounts.get(i) ?? 0;
      if (stroke.points.length > done) {
        canvas.drawStroke(stroke, done);
        drawnCounts.set(i, stroke.points.length);
      }
    }
  },
  { deep: true },
);

watch(color, (v) => canvas.setColor(v));
watch(width, (v) => canvas.setWidth(v));

onMounted(() => {
  if (!canvasEl.value) return;

  canvas.initCanvas(canvasEl.value);
  canvas.setColor(color.value);
  canvas.setWidth(width.value);

  store.currentStrokes.forEach((stroke, i) => {
    canvas.drawStroke(stroke);
    drawnCounts.set(i, stroke.points.length);
  });

  canvas.setStrokeProgressCallback((delta) => {
    if (delta.first) {
      pendingPoints = [];
      pendingStart = true;
    }
    pendingMeta = { color: delta.color, width: delta.width };
    pendingPoints.push(...delta.points);
    scheduleSend();
  });
});

onUnmounted(() => {
  canvas.cleanup();
  if (rafId) cancelAnimationFrame(rafId);
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
