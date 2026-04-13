<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const canvas = useDrawingCanvas();
const { leaveRoom: _leaveRoom } = useLeaveRoom();

const canvasElement = ref<HTMLCanvasElement | null>(null);
const timeLeft = ref(store.drawingTimeLimit);
const timerInterval = ref<number | null>(null);
const hasSubmittedDrawing = ref(false);
const leaveDialogRef = ref<HTMLDialogElement | null>(null);

const category = computed(() => store.localPlayerCard?.category || "Loading...");
const items = computed(() => store.localPlayerCard?.items || []);
const currentScore = computed(() => store.localPlayer?.score || 0);

onMounted(() => {
  if (canvasElement.value) {
    canvas.initCanvas(canvasElement.value);

    if (!store.localPlayerCard) {
      try {
        const saved = localStorage.getItem(STORAGE_KEYS.DRAWING_STATE);
        if (saved) {
          const parsed = JSON.parse(saved) as {
            localPlayerCard?: typeof store.localPlayerCard;
            strokes?: typeof canvas.strokes.value;
          };
          store.localPlayerCard = parsed.localPlayerCard;
          canvas.replaceStrokes(parsed.strokes ?? []);
        }
      } catch {
        localStorage.removeItem(STORAGE_KEYS.DRAWING_STATE);
      }
    }

    startDrawingTimer();
  }
});

onUnmounted(() => {
  try {
    localStorage.setItem(
      STORAGE_KEYS.DRAWING_STATE,
      JSON.stringify({
        localPlayerCard: store.localPlayerCard,
        strokes: canvas.strokes.value,
      }),
    );
  } catch {
    /* localStorage unavailable */
  }
  stopTimer();
  canvas.cleanup();
});

watch(
  () => store.drawingTimeLimit,
  (newRoundLength) => {
    const roundStartTime = store.roundStartTime;
    if (roundStartTime && !Number.isNaN(roundStartTime)) {
      const elapsed = Math.floor((Date.now() - roundStartTime) / 1000);
      timeLeft.value = Math.max(0, newRoundLength - elapsed);
    } else {
      timeLeft.value = newRoundLength;
    }
  },
);

function startDrawingTimer() {
  if (timerInterval.value) return;

  const drawingTimeLimit = store.drawingTimeLimit;
  const roundStartTime = store.roundStartTime;

  if (roundStartTime && !Number.isNaN(roundStartTime)) {
    const elapsed = Math.floor((Date.now() - roundStartTime) / 1000);
    timeLeft.value =
      elapsed < 0 || elapsed > drawingTimeLimit ? drawingTimeLimit : Math.max(0, drawingTimeLimit - elapsed);
  } else {
    timeLeft.value = drawingTimeLimit;
  }

  timerInterval.value = window.setInterval(() => {
    if (roundStartTime && !Number.isNaN(roundStartTime)) {
      const elapsed = Math.floor((Date.now() - roundStartTime) / 1000);
      timeLeft.value = Math.max(0, drawingTimeLimit - elapsed);
    } else {
      timeLeft.value = drawingTimeLimit;
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
  if (store.gamePhase !== "drawing" || hasSubmittedDrawing.value) return;
  hasSubmittedDrawing.value = true;
  stopTimer();

  const drawing = canvas.canvasRef.value?.toDataURL("image/png");
  if (drawing) {
    send({ type: "draw_stroke", playerId: store.localPlayerId, drawing });
  }

  send({ type: "player_ready", playerId: store.localPlayerId });
  localStorage.removeItem(STORAGE_KEYS.DRAWING_STATE);
}

function showLeaveDialog() {
  leaveDialogRef.value?.showModal();
}

function cancelLeave() {
  leaveDialogRef.value?.close();
}

function confirmLeave() {
  leaveDialogRef.value?.close();
  stopTimer();
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
    <!-- Header -->
    <header class="game-header">
      <div class="header-left">
        <button type="button" class="btn-leave" @click="showLeaveDialog">
          <svg
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Leave
        </button>
      </div>

      <div class="timer" :class="{ warning: timeLeft <= 10 }">{{ timeLeft }}</div>

      <div class="header-info">
        <span class="info-round">
          Round {{ store.currentRound }} / {{ store.maxRounds
          }}<span v-if="store.readyCount > 0" class="info-ready"> · {{ store.readyCount }}/{{ store.totalPlayers }} ✓</span>
        </span>
        <span class="info-score">{{ currentScore }} pts</span>
      </div>
    </header>

    <!-- Main layout -->
    <div class="drawing-layout">
      <!-- Category card -->
      <aside class="category-card">
        <h3 class="category-title">{{ category }}</h3>
        <ul class="items-list">
          <li v-for="(item, index) in items" :key="index" class="item">{{ item }}</li>
        </ul>
        <div class="category-actions">
          <button type="button" class="btn-submit" :disabled="hasSubmittedDrawing" @click="endDrawingPhase">
            {{ hasSubmittedDrawing ? "⏳ Waiting…" : "✓ Finish" }}
          </button>
        </div>
      </aside>

      <!-- Canvas panel -->
      <div class="canvas-panel">
        <div class="canvas-tools">
          <div class="tool-group">
            <label class="tool-label">Color</label>
            <input type="color" :value="canvas.currentColor.value" class="color-swatch" @input="handleColorChange">
          </div>
          <div class="tool-group">
            <label class="tool-label">Size</label>
            <input
              type="range"
              min="1"
              max="10"
              :value="canvas.currentWidth.value"
              class="size-slider"
              @input="handleBrushSizeChange"
            >
          </div>
          <button type="button" class="btn-clear" @click="canvas.clear()">🧹 Clear</button>
        </div>
        <canvas ref="canvasElement" class="drawing-canvas" />
        <div class="canvas-actions">
          <button type="button" class="btn-submit" :disabled="hasSubmittedDrawing" @click="endDrawingPhase">
            {{ hasSubmittedDrawing ? "⏳ Waiting…" : "✓ Finish" }}
          </button>
        </div>
      </div>
    </div>

    <!-- Leave confirmation dialog -->
    <dialog ref="leaveDialogRef" class="leave-dialog" @click.self="cancelLeave">
      <h2>Leave Game?</h2>
      <p>Your drawing progress will be lost.</p>
      <div class="dialog-actions">
        <button type="button" class="btn-dialog-cancel" @click="cancelLeave">Stay</button>
        <button type="button" class="btn-dialog-danger" @click="confirmLeave">Leave</button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
/* ── Screen ────────────────────────────────────────────── */
.game-screen {
  width: 100%;
  height: 100dvh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-gradient);
}

/* ── Header ────────────────────────────────────────────── */
.game-header {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  padding: 0.75rem 1.25rem;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.15rem;
  justify-self: end;
}

.info-round {
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.875rem;
  font-weight: 600;
  white-space: nowrap;
}

.info-score {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
}

.timer {
  font-size: 2rem;
  font-weight: 800;
  color: white;
  background: rgba(52, 152, 219, 0.85);
  border-radius: var(--radius-md);
  min-width: 4.5rem;
  text-align: center;
  padding: 0.375rem 1rem;
  line-height: 1.2;
}

.timer.warning {
  background: rgba(231, 76, 60, 0.9);
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.06);
  }
}

.btn-leave {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.4rem 0.75rem;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.22);
  color: rgba(255, 255, 255, 0.6);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-leave:hover {
  background: rgba(255, 255, 255, 0.18);
  border-color: rgba(255, 255, 255, 0.6);
  color: white;
}

.info-ready {
  color: rgba(255, 255, 255, 0.55);
  font-weight: 500;
}

/* ── Drawing layout ────────────────────────────────────── */
.drawing-layout {
  display: flex;
  gap: 1.25rem;
  padding: 1.25rem;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Category card ─────────────────────────────────────── */
.category-card {
  flex: 0 0 240px;
  background: white;
  border-radius: var(--radius-xl);
  padding: 1.25rem;
  box-shadow: var(--shadow-lg);
  height: fit-content;
}

.category-actions {
  display: flex;
  margin-top: 1rem;
}

.category-title {
  margin: 0 0 0.75rem;
  color: var(--color-text-dark);
  font-size: 1.125rem;
  font-weight: 700;
  border-bottom: 2px solid var(--color-primary);
  padding-bottom: 0.5rem;
}

.items-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.25rem;
}

.item {
  padding: 0.4rem 0.6rem;
  background: var(--color-surface);
  border-radius: 4px;
  font-size: 0.875rem;
  color: #495057;
}

/* ── Canvas panel ──────────────────────────────────────── */
.canvas-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.btn-submit {
  width: 100%;
  padding: 0.75rem;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-submit:hover:not(:disabled) {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.72;
  cursor: not-allowed;
  transform: none;
  filter: none;
}

.canvas-actions {
  display: none;
}

.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  align-items: center;
  flex-wrap: wrap;
}

.tool-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.tool-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-muted);
}

.color-swatch {
  width: 2rem;
  height: 1.75rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 4px;
  padding: 0;
  cursor: pointer;
}

.size-slider {
  width: 80px;
  cursor: pointer;
  accent-color: var(--color-primary);
}

.btn-clear {
  margin-left: auto;
  padding: 0.375rem 0.75rem;
  background: var(--color-surface);
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  color: var(--color-text-dark);
}

.btn-clear:hover {
  background: #e9ecef;
}

.drawing-canvas {
  flex: 1;
  min-height: 0;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  cursor: crosshair;
  background: white;
  width: 100%;
  touch-action: none;
}

/* ── Leave dialog ──────────────────────────────────────── */
.leave-dialog {
  border: none;
  border-radius: var(--radius-lg);
  padding: 2rem;
  max-width: 360px;
  width: calc(100% - 2rem);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  margin: 0;
}

.leave-dialog[open] {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.leave-dialog::backdrop {
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
}

.leave-dialog h2 {
  margin: 0 0 0.625rem;
  font-size: 1.25rem;
  color: var(--color-text-dark);
}

.leave-dialog p {
  margin: 0 0 1.5rem;
  color: var(--color-text-muted);
  font-size: 0.9375rem;
}

.dialog-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-dialog-cancel {
  background: none;
  border: 1.5px solid #cbd5e0;
  color: var(--color-text-dark);
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-dialog-cancel:hover {
  background: #f7fafc;
  border-color: #a0aec0;
}

.btn-dialog-danger {
  background: var(--color-danger);
  border: none;
  color: white;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-dialog-danger:hover {
  background: #c82333;
}

/* ── Mobile ────────────────────────────────────────────── */
@media (max-width: 768px) {
  .game-header {
    grid-template-columns: 1fr auto 1fr;
    padding: 0.4rem 0.875rem;
    gap: 0.5rem;
  }

  .timer {
    font-size: 1.5rem;
    padding: 0.25rem 0.75rem;
    min-width: 3rem;
  }

  .drawing-layout {
    flex-direction: column;
    padding: 0.75rem;
    gap: 0.75rem;
  }

  .category-card {
    flex: 0 0 auto;
    padding: 0.875rem;
  }

  .category-title {
    font-size: 1rem;
    margin-bottom: 0.5rem;
  }

  .items-list {
    grid-template-columns: 1fr 1fr;
  }

  .item {
    font-size: 0.8125rem;
    padding: 0.3rem 0.5rem;
  }

  /* On mobile the layout stacks vertically, so give the canvas a sensible floor */
  .drawing-canvas {
    min-height: 260px;
  }

  .category-actions {
    display: none;
  }

  .canvas-actions {
    display: flex;
    margin-top: 1rem;
  }

  .btn-submit {
    width: 100%;
    min-width: 0;
  }
}

</style>
