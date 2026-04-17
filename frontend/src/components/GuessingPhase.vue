<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import ConfirmDialog from "@/components/ConfirmDialog.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameTimer } from "@/composables/useGameTimer";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const router = useRouter();
const { send, disconnect } = useGameConnection();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();

function leaveRoom() {
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

const playerGuesses = ref<Record<string, string[]>>({});
const submittedPlayers = ref<string[]>([]);
const allGuessesSubmitted = ref(false);
const leaveDialogOpen = ref(false);
const skipDialogOpen = ref(false);
const emptyGuessDialogTarget = ref<string | null>(null);

const assignedTargetPlayerId = computed(() => store.guessTargets[store.localPlayerId] || null);
const assignedTargetPlayer = computed(() =>
  assignedTargetPlayerId.value ? store.playersList.find((p) => p.id === assignedTargetPlayerId.value) || null : null,
);
const currentScore = computed(() => store.localPlayer?.score || 0);
const brokenImages = ref<Set<string>>(new Set());

const { timeLeft } = useGameTimer({
  startTime: () => store.guessingStartTime,
  duration: () => store.guessingTimeLimit,
  onExpire: () => autoSubmitGuesses(),
});

onMounted(() => {
  submittedPlayers.value = [];
  if (assignedTargetPlayerId.value) {
    playerGuesses.value[assignedTargetPlayerId.value] = [""];
  }
});

function guessesFor(playerId: string): string[] {
  if (!playerGuesses.value[playerId]) playerGuesses.value[playerId] = [""];
  return playerGuesses.value[playerId] as string[];
}

function onGuessInput(playerId: string, idx: number) {
  const guesses = playerGuesses.value[playerId] || [];
  if (idx === guesses.length - 1 && guesses[idx]?.trim() !== "" && guesses.length < 10) {
    playerGuesses.value[playerId] = [...guesses, ""];
  }
}

function handleGuessKeydown(playerId: string, idx: number, event: KeyboardEvent) {
  if (event.key !== "Enter") return;
  event.preventDefault();
  onGuessInput(playerId, idx);
  nextTick(() => {
    const inputs = document.querySelectorAll<HTMLInputElement>(".guess-input");
    inputs[idx + 1]?.focus();
  });
}

function autoSubmitGuesses() {
  if (!assignedTargetPlayerId.value) return;
  const targetId = assignedTargetPlayerId.value;
  if (!submittedPlayers.value.includes(targetId)) {
    const guesses = (playerGuesses.value[targetId] || []).filter((g) => g.trim() !== "");
    doSubmitGuesses(targetId, guesses);
  }
}

function submitGuessesForPlayer(targetPlayerId: string) {
  const guesses = (playerGuesses.value[targetPlayerId] || []).filter((g) => g.trim() !== "");
  if (guesses.length === 0) {
    emptyGuessDialogTarget.value = targetPlayerId;
    skipDialogOpen.value = true;
    return;
  }
  doSubmitGuesses(targetPlayerId, guesses);
}

function confirmSkipGuesses() {
  const targetPlayerId = emptyGuessDialogTarget.value;
  emptyGuessDialogTarget.value = null;
  if (targetPlayerId) doSubmitGuesses(targetPlayerId, []);
}

function cancelSkipGuesses() {
  emptyGuessDialogTarget.value = null;
}

function doSubmitGuesses(targetPlayerId: string, guesses: string[]) {
  send({ type: "submit_guess", playerId: store.localPlayerId, targetPlayerId, guesses });
  if (!submittedPlayers.value.includes(targetPlayerId)) {
    submittedPlayers.value = [...submittedPlayers.value, targetPlayerId];
  }

  if (assignedTargetPlayerId.value && submittedPlayers.value.includes(assignedTargetPlayerId.value)) {
    allGuessesSubmitted.value = true;
    send({ type: "player_ready", playerId: store.localPlayerId });
  }
}

function handleImageError(playerId: string) {
  brokenImages.value = new Set([...brokenImages.value, playerId]);
}

function showLeaveDialog() {
  if (!shouldConfirm.value) {
    confirmLeave();
    return;
  }
  leaveDialogOpen.value = true;
}

function confirmLeave() {
  leaveRoom();
}
</script>

<template>
  <div class="flex h-dvh w-full flex-col overflow-hidden bg-gradient-to-br from-primary to-secondary">
    <!-- Header -->
    <header
      class="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-4 border-b border-white/10 bg-black/25 px-5 py-3 backdrop-blur-[8px] max-[480px]:gap-1.5 max-[480px]:px-2.5 max-[768px]:gap-2 max-[768px]:px-3.5 max-[768px]:py-2"
    >
      <div class="flex items-center">
        <button
          type="button"
          class="flex cursor-pointer items-center gap-1.5 rounded-[var(--radius-md)] border border-white/[0.22] bg-white/[0.07] px-3 py-1.5 text-[0.8125rem] font-medium text-white/60 transition-all hover:border-white/60 hover:bg-white/[0.18] hover:text-white max-[480px]:px-2.5 max-[480px]:py-1.5 max-[480px]:text-[0.75rem]"
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
          {{ $t("common.leave") }}
        </button>
      </div>

      <div
        class="min-w-[4.5rem] rounded-[var(--radius-md)] px-4 py-1.5 text-center text-[2rem] font-extrabold leading-[1.2] text-white transition-colors max-[480px]:px-2.5 max-[480px]:text-[1.25rem] max-[480px]:py-[0.2rem] max-[768px]:min-w-12 max-[768px]:px-3 max-[768px]:py-1 max-[768px]:text-2xl"
        :class="timeLeft <= 10 ? 'animate-timer-pulse bg-[rgba(231,76,60,0.9)]' : 'bg-[rgba(52,152,219,0.85)]'"
      >
        {{ timeLeft }}
      </div>

      <div class="flex flex-col items-end gap-0.5 justify-self-end">
        <span class="whitespace-nowrap text-sm font-semibold text-white/95">
          {{ $t("common.roundProgress", { current: store.currentRound, total: store.maxRounds }) }}
          <span v-if="store.readyCount > 0" class="font-medium text-white/55">
            · {{ store.readyCount }}/{{ store.totalPlayers }}
            ✓</span
          >
        </span>
        <span class="whitespace-nowrap text-[0.8125rem] font-medium text-white/70">
          {{ $t("common.pointsShort", { count: currentScore }) }}
        </span>
      </div>
    </header>

    <!-- Main content -->
    <div
      class="flex min-h-0 flex-1 flex-row gap-5 overflow-hidden p-5 max-[768px]:flex-col max-[768px]:gap-3 max-[768px]:p-3"
    >
      <template v-if="assignedTargetPlayer">
        <!-- Drawing panel -->
        <div
          class="flex min-h-0 min-w-0 [flex:1.2] flex-col overflow-hidden rounded-[var(--radius-xl)] bg-white p-5 shadow-[var(--shadow-lg)] max-[768px]:flex-none max-[768px]:p-3.5"
        >
          <h2 class="mb-3.5 mt-0 shrink-0 border-b-2 border-primary pb-2 text-lg font-bold text-ink-dark">
            {{ $t("guessing.guessPlayerDrawing", { name: assignedTargetPlayer.name }) }}
          </h2>
          <div
            class="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-[var(--radius-md)] border-[1.5px] border-[#e2e8f0] bg-surface max-[768px]:h-[min(155px,26dvh)] max-[768px]:flex-none"
          >
            <img
              v-if="assignedTargetPlayer.drawing && !brokenImages.has(assignedTargetPlayer.id)"
              :src="assignedTargetPlayer.drawing"
              :alt="$t('guessing.playerDrawingAlt')"
              class="max-h-full max-w-full object-contain"
              @error="handleImageError(assignedTargetPlayer.id)"
            >
            <p v-else-if="brokenImages.has(assignedTargetPlayer.id)" class="italic text-ink-muted">
              {{ $t("guessing.drawingFailed") }}
            </p>
            <p v-else class="italic text-ink-muted">{{ $t("guessing.waitingForDrawing") }}</p>
          </div>
        </div>

        <!-- Guessing panel -->
        <div class="flex min-h-0 min-w-0 flex-1 flex-col max-[768px]:overflow-y-auto">
          <div
            v-if="submittedPlayers.includes(assignedTargetPlayer.id)"
            class="flex w-full items-center gap-2.5 self-start rounded-[var(--radius-md)] border border-[#c3e6cb] bg-[#d4edda] px-5 py-4 text-base font-semibold text-[#155724]"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            {{ $t("guessing.submittedWaiting") }}
          </div>
          <div v-else class="flex flex-col gap-3.5 rounded-[var(--radius-xl)] bg-white p-5 shadow-[var(--shadow-lg)]">
            <h3
              class="m-0 flex shrink-0 items-center gap-2 text-[0.9375rem] font-semibold tracking-[0.04em] text-ink-muted uppercase"
            >
              {{ $t("guessing.yourGuesses") }}
              <span
                class="rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-[0.8125rem] font-bold normal-case tracking-normal text-primary"
              >
                {{ guessesFor(assignedTargetPlayer.id).filter(g => g.trim()).length }}
                / 10
              </span>
            </h3>
            <div class="grid grid-cols-2 gap-2 max-[768px]:grid-cols-1">
              <input
                v-for="(_, idx) in guessesFor(assignedTargetPlayer.id)"
                :key="idx"
                v-model="guessesFor(assignedTargetPlayer.id)[idx]"
                type="text"
                :placeholder="$t('guessing.guessNumber', { number: idx + 1 })"
                enterkeyhint="next"
                class="guess-input rounded-[var(--radius-md)] border-[1.5px] border-[#e2e8f0] px-3 py-2.5 text-[0.9375rem] text-ink-dark transition-[border-color] focus:border-primary focus:shadow-[0_0_0_3px_rgba(102,126,234,0.25)] focus:outline-none"
                @input="onGuessInput(assignedTargetPlayer.id, idx)"
                @keydown="handleGuessKeydown(assignedTargetPlayer.id, idx, $event)"
              >
            </div>
            <button
              type="button"
              class="shrink-0 cursor-pointer rounded-[var(--radius-md)] border-none bg-gradient-to-br from-primary to-secondary p-3 text-base font-bold text-white transition-all hover:-translate-y-px hover:brightness-[1.08]"
              @click="submitGuessesForPlayer(assignedTargetPlayer.id)"
            >
              {{ $t("guessing.submitGuesses") }}
            </button>
          </div>
        </div>
      </template>

      <div v-else class="flex w-full items-center justify-center text-[1.0625rem] text-white/80">
        <p class="italic text-ink-muted">{{ $t("guessing.waitingForAssignedDrawing") }}</p>
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

    <ConfirmDialog
      v-model:open="skipDialogOpen"
      :title="$t('guessing.noGuessesTitle')"
      :message="$t('guessing.noGuessesMessage')"
      :confirm-label="$t('guessing.submitAnyway')"
      :cancel-label="$t('guessing.goBack')"
      variant="primary"
      @confirm="confirmSkipGuesses"
      @cancel="cancelSkipGuesses"
    />
  </div>
</template>
