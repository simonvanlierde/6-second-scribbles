<template>
  <div class="shared-drawpad">
    <div class="canvas-tools">
      <div class="tool-group">
        <label>Color:</label>
        <input type="color" v-model="color">
      </div>
      <div class="tool-group">
        <label>Size:</label>
        <input type="range" min="1" max="20" v-model.number="width">
      </div>
      <div class="tool-group"><button type="button" class="btn btn-small" @click="clearLocal">Clear</button></div>
    </div>
    <canvas ref="canvasEl" class="mini-canvas"></canvas>
    <p class="drawpad-hint">Draw together with other players while waiting!</p>
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

<style scoped>
.shared-drawpad {
  display: block;
}
.canvas-tools {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
  align-items: center;
}
.tool-group {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}
.tool-group label {
  font-size: 0.875rem;
  font-weight: 500;
}
.mini-canvas {
  width: 100%;
  height: 200px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
  touch-action: none; /* Prevent scrolling while drawing */
  cursor: crosshair;
}
.drawpad-hint {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #6c757d;
  text-align: center;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .mini-canvas {
    height: 180px;
  }

  .canvas-tools {
    font-size: 0.875rem;
  }

  .tool-group label {
    font-size: 0.75rem;
  }

  .drawpad-hint {
    font-size: 0.75rem;
  }
}

@media (max-width: 480px) {
  .mini-canvas {
    height: 150px;
  }

  .canvas-tools {
    gap: 0.375rem;
  }

  .btn-small {
    padding: 0.375rem 0.625rem;
    font-size: 0.75rem;
  }
}
</style>
