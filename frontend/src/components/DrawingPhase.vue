<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { useDrawingCanvas } from "@/composables/useDrawingCanvas";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameTimer } from "@/composables/useGameTimer";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const router = useRouter();
const { send, disconnect } = useGameConnection();
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

const category = computed(() => store.localPlayerCard?.category || "Loading...");
const items = computed(() => store.localPlayerCard?.items || []);
const currentScore = computed(() => store.localPlayer?.score || 0);

const { timeLeft, stop: stopTimer } = useGameTimer({
  startTime: () => store.roundStartTime,
  duration: () => store.drawingTimeLimit,
  onExpire: () => endDrawingPhase(),
});

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

function handleColorChange(event: Event) {
  canvas.setColor((event.target as HTMLInputElement).value);
}

function handleBrushSizeChange(event: Event) {
  canvas.setWidth(Number((event.target as HTMLInputElement).value));
}
</script>

<template>
  <div class="flex h-dvh w-full flex-col overflow-hidden bg-gradient-to-br from-primary to-secondary">
    <!-- Header -->
    <header
      class="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-4 border-b border-white/10 bg-black/25 px-5 py-3 backdrop-blur-[8px] max-[768px]:gap-2 max-[768px]:px-3.5 max-[768px]:py-1.5"
    >
      <div class="flex items-center">
        <button
          type="button"
          class="flex cursor-pointer items-center gap-1.5 rounded-[var(--radius-md)] border border-white/[0.22] bg-white/[0.07] px-3 py-1.5 text-[0.8125rem] font-medium text-white/60 transition-all hover:border-white/60 hover:bg-white/[0.18] hover:text-white max-[480px]:px-2.5 max-[480px]:text-[0.75rem]"
          @click="showLeaveDialog"
        >
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

      <div
        class="min-w-[4.5rem] rounded-[var(--radius-md)] px-4 py-1.5 text-center text-[2rem] font-extrabold leading-[1.2] text-white transition-colors max-[480px]:px-2.5 max-[480px]:text-xl max-[768px]:min-w-12 max-[768px]:px-3 max-[768px]:py-1 max-[768px]:text-2xl"
        :class="timeLeft <= 10 ? 'animate-timer-pulse bg-[rgba(231,76,60,0.9)]' : 'bg-[rgba(52,152,219,0.85)]'"
      >
        {{ timeLeft }}
      </div>

      <div class="flex flex-col items-end gap-0.5 justify-self-end">
        <span class="whitespace-nowrap text-sm font-semibold text-white/95">
          Round {{ store.currentRound }} / {{ store.maxRounds }}
          <span v-if="store.readyCount > 0" class="font-medium text-white/55">
            · {{ store.readyCount }}/{{ store.totalPlayers }}
            ✓</span
          >
        </span>
        <span class="whitespace-nowrap text-[0.8125rem] font-medium text-white/70">{{ currentScore }} pts</span>
      </div>
    </header>

    <!-- Main layout -->
    <div class="flex min-h-0 flex-1 gap-5 overflow-hidden p-5 max-[768px]:flex-col max-[768px]:gap-3 max-[768px]:p-3">
      <!-- Category card -->
      <aside
        class="h-fit w-60 shrink-0 rounded-[var(--radius-xl)] bg-white p-5 shadow-[var(--shadow-lg)] max-[768px]:w-auto max-[768px]:p-3.5"
      >
        <h3
          class="mb-3 mt-0 border-b-2 border-primary pb-2 text-lg font-bold text-ink-dark max-[768px]:mb-2 max-[768px]:text-base"
        >
          {{ category }}
        </h3>
        <ul class="m-0 grid list-none grid-cols-1 gap-1 p-0 max-[768px]:grid-cols-2">
          <li
            v-for="(item, index) in items"
            :key="index"
            class="rounded bg-surface px-2.5 py-1.5 text-sm text-[#495057] max-[768px]:px-2 max-[768px]:py-1 max-[768px]:text-[0.8125rem]"
          >
            {{ item }}
          </li>
        </ul>
        <div class="mt-4 flex max-[768px]:hidden">
          <button
            type="button"
            class="w-full cursor-pointer rounded-[var(--radius-md)] border-none bg-gradient-to-br from-primary to-secondary p-3 text-base font-bold text-white transition-all hover:-translate-y-px hover:brightness-[1.08] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-[0.72]"
            :disabled="hasSubmittedDrawing"
            @click="endDrawingPhase"
          >
            {{ hasSubmittedDrawing ? "⏳ Waiting…" : "✓ Finish" }}
          </button>
        </div>
      </aside>

      <!-- Canvas panel -->
      <div
        class="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-[var(--radius-xl)] bg-white p-4 shadow-[var(--shadow-lg)]"
      >
        <div class="mb-3 flex flex-wrap items-center gap-4 border-b border-[#e2e8f0] pb-3">
          <div class="flex items-center gap-2">
            <label class="text-[0.8125rem] font-semibold text-ink-muted">Color</label>
            <input
              type="color"
              :value="canvas.currentColor.value"
              class="h-7 w-8 cursor-pointer rounded border-[1.5px] border-[#e2e8f0] p-0"
              @input="handleColorChange"
            >
          </div>
          <div class="flex items-center gap-2">
            <label class="text-[0.8125rem] font-semibold text-ink-muted">Size</label>
            <input
              type="range"
              min="1"
              max="10"
              :value="canvas.currentWidth.value"
              class="w-20 cursor-pointer accent-primary"
              @input="handleBrushSizeChange"
            >
          </div>
          <button
            type="button"
            class="ml-auto cursor-pointer rounded-[var(--radius-sm)] border-[1.5px] border-[#e2e8f0] bg-surface px-3 py-1.5 text-[0.8125rem] font-semibold text-ink-dark transition-all hover:bg-[#e9ecef]"
            @click="canvas.clear()"
          >
            🧹 Clear
          </button>
        </div>
        <canvas
          ref="canvasElement"
          class="min-h-0 w-full flex-1 cursor-crosshair touch-none rounded-[var(--radius-md)] border-[1.5px] border-[#e2e8f0] bg-white max-[768px]:min-h-[260px]"
        />
        <div class="mt-4 hidden max-[768px]:flex">
          <button
            type="button"
            class="w-full cursor-pointer rounded-[var(--radius-md)] border-none bg-gradient-to-br from-primary to-secondary p-3 text-base font-bold text-white transition-all hover:-translate-y-px hover:brightness-[1.08] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-[0.72]"
            :disabled="hasSubmittedDrawing"
            @click="endDrawingPhase"
          >
            {{ hasSubmittedDrawing ? "⏳ Waiting…" : "✓ Finish" }}
          </button>
        </div>
      </div>
    </div>

    <ConfirmDialog
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
