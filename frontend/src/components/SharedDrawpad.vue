<template>
  <div>
    <div class="mb-2 flex flex-wrap items-center gap-2 max-[768px]:text-sm max-[480px]:gap-1.5">
      <div class="flex items-center gap-1">
        <label class="text-sm font-medium max-[768px]:text-xs">Color:</label>
        <input v-model="color" type="color">
      </div>
      <div class="flex items-center gap-1">
        <label class="text-sm font-medium max-[768px]:text-xs">Size:</label>
        <input v-model.number="width" type="range" min="1" max="20">
      </div>
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="cursor-pointer rounded-md border-0 px-4 py-2 text-sm font-semibold transition-all max-[480px]:px-2.5 max-[480px]:py-1.5 max-[480px]:text-xs"
          @click="clearLocal"
        >
          Clear
        </button>
      </div>
    </div>
    <canvas
      ref="canvasEl"
      class="mini-canvas h-[200px] w-full cursor-crosshair touch-none rounded border border-gray-300 bg-white max-[768px]:h-[180px] max-[480px]:h-[150px]"
    />
    <p class="mt-2 text-center text-sm text-gray-500 max-[768px]:text-xs">
      Draw together with other players while waiting!
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";

import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import type { DrawStroke } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const canvas = useDrawingCanvas();
const canvasEl = ref<HTMLCanvasElement | null>(null);
const store = useGameStore();
const { send } = useGameConnection();

const color = ref("#000000");
const width = ref(5);

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
