<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import GameHeader from "@/components/game/GameHeader.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdIconButton from "@/components/ui/HdIconButton.vue";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameTimer } from "@/composables/useGameTimer";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { useSound } from "@/composables/useSound";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

// Fixed pen palette — drawing colours must be theme-independent so the exported
// PNG looks the same for every viewer regardless of light/dark mode.
const PALETTE = ["#2d2d2d", "#ff4d4d", "#2d5da1", "#2e9e5b", "#ff8c42"] as const;
const BRUSH_SIZES = [3, 6, 10] as const;

const store = useGameStore();
const router = useRouter();
const { send, disconnect } = useGameConnection();
const { play } = useSound();
const canvas = useDrawingCanvas();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();

function leaveRoom() {
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

const canvasElement = ref<HTMLCanvasElement | null>(null);
const hasSubmittedDrawing = ref(false);
const leaveDialogOpen = ref(false);
const doneItems = ref<Set<number>>(new Set());

const category = computed(() => store.localPlayerCard?.category || i18n.global.t("drawing.loadingCategory"));
const items = computed(() => store.localPlayerCard?.items || []);

const { timeLeft, stop: stopTimer } = useGameTimer({
  startTime: () => store.roundStartTime,
  duration: () => store.drawingTimeLimit,
  onExpire: () => endDrawingPhase(),
});

// Last-10-seconds tick.
watch(timeLeft, (left) => {
  if (left > 0 && left <= 10) play("tick");
});

onMounted(() => {
  play("roundStart");
  canvas.setColor(PALETTE[0]);
  canvas.setWidth(BRUSH_SIZES[1]);

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
  canvas.cleanup();
});

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

function finishDrawing() {
  play("click");
  endDrawingPhase();
}

function toggleItem(index: number) {
  const next = new Set(doneItems.value);
  if (next.has(index)) next.delete(index);
  else next.add(index);
  doneItems.value = next;
}

function showLeaveDialog() {
  if (!shouldConfirm.value) {
    confirmLeave();
    return;
  }
  leaveDialogOpen.value = true;
}

function confirmLeave() {
  stopTimer();
  leaveRoom();
}
</script>

<template>
  <div class="drawing-phase">
    <GameHeader :time-left="timeLeft" @leave="showLeaveDialog" />

    <div class="drawing-phase__body">
      <!-- Category sidebar -->
      <aside class="drawing-phase__sidebar">
        <HdCard class="category-card">
          <h3 class="category-card__title">{{ category }}</h3>
          <ol class="category-card__list">
            <li v-for="(item, index) in items" :key="index">
              <button
                type="button"
                class="category-card__item"
                :class="{ 'category-card__item--done': doneItems.has(index) }"
                :aria-pressed="doneItems.has(index)"
                @click="toggleItem(index)"
              >
                <span class="category-card__num">{{ index + 1 }}</span>
                <span class="category-card__text">{{ item }}</span>
              </button>
            </li>
          </ol>
        </HdCard>

        <HdCard variant="postit" class="drawing-phase__hint">{{ $t("drawing.hint") }}</HdCard>

        <HdButton
          variant="success"
          class="drawing-phase__finish-desktop"
          :disabled="hasSubmittedDrawing"
          @click="finishDrawing"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
          {{ hasSubmittedDrawing ? $t("drawing.waiting") : $t("drawing.finish") }}
        </HdButton>
      </aside>

      <!-- Canvas panel -->
      <div class="drawing-phase__canvas-panel">
        <div class="toolbar">
          <div class="toolbar__group" role="group" :aria-label="$t('drawing.color')">
            <button
              v-for="color in PALETTE"
              :key="color"
              type="button"
              class="swatch"
              :class="{ 'swatch--active': canvas.currentColor.value === color }"
              :style="{ background: color }"
              :aria-label="color"
              :aria-pressed="canvas.currentColor.value === color"
              @click="canvas.setColor(color)"
            />
          </div>
          <div class="toolbar__group" role="group" :aria-label="$t('drawing.size')">
            <button
              v-for="size in BRUSH_SIZES"
              :key="size"
              type="button"
              class="brush"
              :class="{ 'brush--active': canvas.currentWidth.value === size }"
              :aria-label="`${size}`"
              :aria-pressed="canvas.currentWidth.value === size"
              @click="canvas.setWidth(size)"
            >
              <span class="brush__dot" :style="{ width: `${size + 4}px`, height: `${size + 4}px` }" />
            </button>
          </div>
          <div class="toolbar__group toolbar__group--end">
            <HdIconButton :label="$t('drawing.undo')" @click="canvas.undo()">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M3 7v6h6" />
                <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13" />
              </svg>
            </HdIconButton>
            <HdIconButton :label="$t('drawing.clear')" @click="canvas.clear()">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M3 6h18" />
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14" />
              </svg>
            </HdIconButton>
          </div>
        </div>

        <div class="canvas-stage"><canvas ref="canvasElement" class="canvas-stage__canvas" /></div>

        <HdButton
          variant="success"
          class="drawing-phase__finish-mobile"
          :disabled="hasSubmittedDrawing"
          @click="finishDrawing"
        >
          {{ hasSubmittedDrawing ? $t("drawing.waiting") : $t("drawing.finish") }}
        </HdButton>
      </div>
    </div>

    <HdDialog
      v-model:open="leaveDialogOpen"
      :title="leaveDialog.title"
      :message="leaveDialog.message"
      :confirm-label="leaveDialog.confirmLabel"
      :cancel-label="leaveDialog.cancelLabel"
      variant="danger"
      @confirm="confirmLeave"
    />
  </div>
</template>

<style scoped>
.drawing-phase {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: var(--color-paper);
}
.drawing-phase__body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: var(--space-4);
  padding: var(--space-4);
  overflow: hidden;
}
.drawing-phase__sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 240px;
  flex-shrink: 0;
  overflow-y: auto;
}
.category-card__title {
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 2.5px solid var(--color-marker-red);
  font-size: var(--text-heading-sm);
}
.category-card__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.category-card__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  background: transparent;
  border: 0;
  padding: 6px 4px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  text-align: left;
  border-radius: 6px;
}
.category-card__item:hover {
  background: color-mix(in srgb, var(--color-ink) 6%, transparent);
}
.category-card__num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-label-sm);
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
}
.category-card__item--done .category-card__text {
  text-decoration: line-through wavy var(--color-marker-red);
  color: var(--color-ink-muted);
}
.category-card__item--done .category-card__num {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
}
.drawing-phase__hint {
  font-size: var(--text-label-md);
}
.drawing-phase__finish-desktop {
  margin-top: auto;
}
.drawing-phase__finish-desktop svg {
  width: 20px;
  height: 20px;
}
.drawing-phase__finish-mobile {
  display: none;
}

.drawing-phase__canvas-panel {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
  gap: var(--space-3);
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}
.toolbar__group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.toolbar__group--end {
  margin-left: auto;
  gap: var(--space-1);
}
.swatch {
  width: 28px;
  height: 28px;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  cursor: pointer;
  padding: 0;
  transition: transform var(--motion-fast) var(--ease-spring);
}
.swatch--active {
  transform: scale(1.15) rotate(-3deg);
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.brush {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--color-card);
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  cursor: pointer;
  padding: 0;
}
.brush--active {
  background: var(--color-highlighter-yellow);
}
.brush__dot {
  display: inline-block;
  background: var(--color-ink);
  border-radius: 50%;
}
.canvas-stage {
  position: relative;
  flex: 1;
  min-height: 0;
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  background-color: var(--color-card);
  /* Faint 20px dot grid for paper feel. */
  background-image: radial-gradient(color-mix(in srgb, var(--color-ink) 16%, transparent) 1px, transparent 1px);
  background-size: 20px 20px;
  overflow: hidden;
}
.canvas-stage__canvas {
  display: block;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: crosshair;
}

@media (max-width: 768px) {
  .drawing-phase__body {
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    overflow-y: auto;
  }
  .drawing-phase__sidebar {
    width: auto;
    flex-shrink: 0;
    overflow-y: visible;
  }
  /* Two columns (column-major: 1–5 left, 6–10 right) to reclaim vertical space. */
  .category-card__list {
    display: block;
    columns: 2;
    column-gap: var(--space-5);
  }
  .category-card__list li {
    break-inside: avoid;
    margin-bottom: var(--space-1);
  }
  .category-card__item {
    font-size: var(--text-body-lg);
  }
  .drawing-phase__finish-desktop {
    display: none;
  }
  .drawing-phase__finish-mobile {
    display: inline-flex;
  }
  .canvas-stage {
    min-height: 260px;
  }
}
</style>
