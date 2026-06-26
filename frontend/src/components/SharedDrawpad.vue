<template>
  <div>
    <div class="mb-2">
      <DrawingToolbar
        :current-color="color"
        :current-width="width"
        @select-color="color = $event"
        @select-size="width = $event"
        @undo="canvas.undo()"
        @clear="clearLocal"
      />
    </div>
    <canvas
      ref="canvasEl"
      class="mini-canvas h-[200px] w-full cursor-crosshair touch-none rounded border border-gray-300 bg-white max-[768px]:h-[180px] max-[480px]:h-[150px]"
    />
    <p class="mt-2 text-center text-sm text-gray-500 max-[768px]:text-xs">{{ $t("lobby.drawTogetherWhileWaiting") }}</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";

import DrawingToolbar from "@/components/DrawingToolbar.vue";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { BRUSH_SIZES, DRAW_PALETTE } from "@/config/drawing";
import type { DrawStroke } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const canvas = useDrawingCanvas();
const canvasEl = ref<HTMLCanvasElement | null>(null);
const store = useGameStore();
const { send } = useGameConnection();

const color = ref<string>(DRAW_PALETTE[0]);
const width = ref<number>(BRUSH_SIZES[1]);

let rafId: number | null = null;
let latestPartial: DrawStroke | null = null;

function clearLocal() {
  canvas.clear();
}

function scheduleSend() {
  if (rafId !== null) return;
  rafId = requestAnimationFrame(() => {
    rafId = null;
    if (latestPartial && store.localPlayerId) {
      send({ type: "draw_stroke_partial", playerId: store.localPlayerId, stroke: latestPartial });
    }
  });
}

// Draw incoming strokes from store
watch(
  () => store.currentStrokes,
  (strokes) => {
    if (strokes.length === 0) {
      canvas.clear();
      return;
    }

    const last = strokes[strokes.length - 1];
    if (last) canvas.drawStroke(last);
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

  for (const s of store.currentStrokes) canvas.drawStroke(s);

  canvas.setStrokeProgressCallback((partial) => {
    latestPartial = partial;
    scheduleSend();
  });
});

onUnmounted(() => {
  canvas.cleanup();
  if (rafId) cancelAnimationFrame(rafId);
});
</script>
