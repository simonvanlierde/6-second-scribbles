<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, ref, watch } from "vue";
import { gameEngineKey } from "@/composables/injectionKeys";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const canvas = useDrawingCanvas();
// biome-ignore lint/style/noNonNullAssertion: always provided by App.vue
const gameEngineRef = inject(gameEngineKey)!;
const { leaveRoom: _leaveRoom } = useLeaveRoom(gameEngineRef);

const canvasElement = ref<HTMLCanvasElement | null>(null);
const timeLeft = ref(store.roundLength);
const timerInterval = ref<number | null>(null);

const category = computed(() => store.localPlayerCard?.category || "Loading...");
const items = computed(() => store.localPlayerCard?.items || []);
const currentScore = computed(() => store.localPlayer?.score || 0);

onMounted(() => {
  // Restore in-progress drawing from localStorage on page reload.
  // Uses a separate key ("drawingState") so it never clobbers the store's
  // full "gameState" snapshot which has ~12 fields.
  if (!store.localPlayerCard) {
    try {
      const saved = localStorage.getItem("drawingState");
      if (saved) {
        const parsed = JSON.parse(saved);
        store.setLocalPlayerCard(parsed.localPlayerCard);
        canvas.loadDrawing(parsed.drawing);
      }
    } catch {
      localStorage.removeItem("drawingState");
    }
  }

  if (canvasElement.value) {
    canvas.initCanvas(canvasElement.value);
    startDrawingTimer();
  }
});

onUnmounted(() => {
  // Persist drawing so a page reload can restore it.
  // Use "drawingState" — a dedicated key that does not collide with the
  // store's "gameState" watcher.
  localStorage.setItem(
    "drawingState",
    JSON.stringify({
      localPlayerCard: store.localPlayerCard,
      drawing: canvas.toDataURL(),
    }),
  );
  stopTimer();
  canvas.cleanup();
});

// Recalculate timeLeft if roundLength is updated (e.g. late settings sync)
watch(
  () => store.roundLength,
  (newRoundLength) => {
    timeLeft.value = newRoundLength;
  },
);

function startDrawingTimer() {
  if (timerInterval.value) return;

  const roundLength = store.roundLength;
  const roundStartTime = store.roundStartTime;

  if (roundStartTime && !Number.isNaN(roundStartTime)) {
    const elapsed = Math.floor((Date.now() - roundStartTime) / 1000);
    timeLeft.value = elapsed < 0 || elapsed > roundLength ? roundLength : Math.max(0, roundLength - elapsed);
  } else {
    timeLeft.value = roundLength;
  }

  timerInterval.value = window.setInterval(() => {
    if (roundStartTime && !Number.isNaN(roundStartTime)) {
      const elapsed = Math.floor((Date.now() - roundStartTime) / 1000);
      timeLeft.value = Math.max(0, roundLength - elapsed);
    } else {
      timeLeft.value = roundLength;
    }

    if (timeLeft.value <= 0) {
      stopTimer();
      endDrawingPhase();
    }
  }, 1000);
}

function stopTimer() {
  if (timerInterval.value) {
    clearInterval(timerInterval.value);
    timerInterval.value = null;
  }
}

function endDrawingPhase() {
  if (store.gamePhase !== "drawing") return;

  send({ type: "drawing_complete", playerId: store.localPlayerId, drawing: canvas.toDataURL() });
  send({ type: "player_ready", playerId: store.localPlayerId });
  localStorage.removeItem("drawingState");
}

function leaveRoom() {
  stopTimer(); // stop timer immediately; onUnmounted also cleans up
  _leaveRoom();
}

function handleColorChange(event: Event) {
  canvas.setColor((event.target as HTMLInputElement).value);
}

function handleBrushSizeChange(event: Event) {
  canvas.setWidth(Number((event.target as HTMLInputElement).value));
}
</script>

<template>
  <div class="game-screen">
    <div class="game-header">
      <div class="round-info">Round {{ store.currentRound }} of {{ store.maxRounds }}</div>
      <div class="timer" :class="{ warning: timeLeft <= 10 }">{{ timeLeft }}</div>
      <div class="score">Score: {{ currentScore }}</div>
      <button type="button" class="btn btn-secondary btn-leave" @click="leaveRoom">🚪 Leave</button>
    </div>

    <div v-if="store.readyCount > 0" class="ready-status-header">
      <p class="ready-count-small">{{ store.readyCount }} / {{ store.totalPlayers }} players finished drawing</p>
    </div>

    <div class="drawing-container">
      <div class="category-card">
        <h3>{{ category }}</h3>
        <ul class="items-list">
          <li v-for="(item, index) in items" :key="index">{{ item }}</li>
        </ul>
      </div>

      <div class="canvas-container">
        <div class="canvas-tools">
          <div class="tool-group">
            <label>Color:</label>
            <input type="color" :value="canvas.currentColor.value" @input="handleColorChange">
          </div>
          <div class="tool-group">
            <label>Size:</label>
            <input type="range" min="1" max="10" :value="canvas.currentWidth.value" @input="handleBrushSizeChange">
          </div>
          <button type="button" class="btn btn-small" @click="canvas.clear()">Clear</button>
        </div>
        <canvas ref="canvasElement" class="drawing-canvas" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.game-screen {
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.game-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #2c3e50;
  color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.ready-status-header {
  padding: 0.5rem 2rem;
  background-color: #e7f3ff;
  text-align: center;
}

.ready-count-small {
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  margin: 0;
}

.round-info,
.score {
  font-size: 1.125rem;
  font-weight: 500;
}

.timer {
  font-size: 2rem;
  font-weight: bold;
  padding: 0.5rem 1.5rem;
  background-color: #3498db;
  border-radius: var(--radius-md);
  min-width: 100px;
  text-align: center;
}

.timer.warning {
  background-color: #e74c3c;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
}

.drawing-container {
  display: flex;
  gap: 2rem;
  padding: 2rem;
  flex: 1;
}

.category-card {
  flex: 0 0 300px;
  background: white;
  padding: 1.5rem;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  height: fit-content;
}

.category-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.items-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.items-list li {
  padding: 0.5rem;
  margin: 0.25rem 0;
  background-color: var(--color-surface);
  border-radius: 4px;
  font-size: 0.875rem;
}

.canvas-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 1rem;
}

.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
  align-items: center;
}

.tool-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.tool-group label {
  font-weight: 500;
  font-size: 0.875rem;
}

.drawing-canvas {
  flex: 1;
  border: 2px solid var(--color-border);
  border-radius: 4px;
  cursor: crosshair;
  background: white;
  width: 100%;
  min-height: 400px;
  touch-action: none;
}

@media (max-width: 768px) {
  .game-header {
    padding: 0.75rem 1rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .round-info,
  .score {
    font-size: 0.875rem;
  }

  .timer {
    font-size: 1.5rem;
    padding: 0.375rem 1rem;
    min-width: 80px;
  }

  .btn-leave {
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
  }

  .drawing-container {
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
  }

  .category-card {
    flex: 0 0 auto;
    padding: 1rem;
  }

  .category-card h3 {
    font-size: 1.25rem;
  }

  .canvas-container {
    padding: 0.75rem;
  }

  .canvas-tools {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .tool-group {
    font-size: 0.875rem;
  }

  .drawing-canvas {
    min-height: 300px;
  }
}

@media (max-width: 480px) {
  .game-header {
    font-size: 0.875rem;
  }

  .timer {
    font-size: 1.25rem;
    padding: 0.25rem 0.75rem;
    min-width: 60px;
  }

  .drawing-container {
    padding: 0.5rem;
  }

  .category-card {
    padding: 0.75rem;
  }

  .items-list li {
    font-size: 0.75rem;
    padding: 0.375rem;
  }

  .drawing-canvas {
    min-height: 250px;
  }

  .canvas-tools {
    font-size: 0.75rem;
  }
}
</style>
