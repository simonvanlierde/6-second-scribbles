<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import DrawingCanvasStage from "@/components/DrawingCanvasStage.vue";
import DrawingToolbar from "@/components/DrawingToolbar.vue";
import GameHeader from "@/components/game/GameHeader.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameTimer } from "@/composables/useGameTimer";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { useRoundDraft } from "@/composables/useRoundDraft";
import { useSound } from "@/composables/useSound";
import { BRUSH_SIZES, DRAW_PALETTE } from "@/config/drawing";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const { play } = useSound();
const canvas = useDrawingCanvas();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();
const { leaveRoom } = useLeaveRoom();

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

// In-progress strokes are the one piece of drawing state the server doesn't hold
// until submit, so they're drafted locally and restored on reconnect. The card
// is restored from the authoritative room_state snapshot (see applyRoomState);
// the saved copy here is only a pre-snapshot fallback.
const draft = useRoundDraft<{ localPlayerCard: typeof store.localPlayerCard; strokes: typeof canvas.strokes.value }>(
  STORAGE_KEYS.DRAWING_STATE,
  {
    round: () => store.currentRound,
    collect: () => ({ localPlayerCard: store.localPlayerCard, strokes: canvas.strokes.value }),
    apply: (data) => {
      if (!store.localPlayerCard && data.localPlayerCard) store.localPlayerCard = data.localPlayerCard;
      if (data.strokes) canvas.replaceStrokes(data.strokes);
    },
    active: () => !hasSubmittedDrawing.value,
  },
);

onMounted(() => {
  play("roundStart");
  canvas.setColor(DRAW_PALETTE[0]);
  canvas.setWidth(BRUSH_SIZES[1]);

  if (canvasElement.value) {
    canvas.initCanvas(canvasElement.value);
    draft.restore();
  }
});

onUnmounted(() => {
  canvas.cleanup();
});

function endDrawingPhase() {
  if (hasSubmittedDrawing.value) return;
  hasSubmittedDrawing.value = true;
  // Keep the timer running: it shows the shared round countdown, which still
  // ticks for everyone else after this player submits early.

  const drawing = canvas.canvasRef.value?.toDataURL("image/png");
  if (drawing) {
    send({ type: "draw_stroke", playerId: store.localPlayerId, drawing });
    // Keep our own copy too — the receive handler skips own-player strokes, so
    // without this the end-of-game gallery would miss this player's drawing.
    store.setPlayerDrawing(store.localPlayerId, drawing);
  }

  send({ type: "player_ready", playerId: store.localPlayerId });
  draft.clear();
}

// Safety net for the race where `start_guessing` arrives before this client's
// local timer fires: submit the drawing while the canvas is still mounted.
// `hasSubmittedDrawing` keeps Finish / timer / this watcher to a single send.
watch(
  () => store.gamePhase,
  (phase) => {
    if (phase === "guessing") endDrawingPhase();
  },
);

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
        <DrawingToolbar
          :current-color="canvas.currentColor.value"
          :current-width="canvas.currentWidth.value"
          @select-color="canvas.setColor"
          @select-size="canvas.setWidth"
          @undo="canvas.undo()"
          @clear="canvas.clear()"
        />

        <DrawingCanvasStage class="drawing-phase__stage"><canvas ref="canvasElement" /></DrawingCanvasStage>

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
.drawing-phase__stage {
  flex: 1;
  min-height: 0;
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
