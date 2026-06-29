<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";

import GameHeader from "@/components/game/GameHeader.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdPill from "@/components/ui/HdPill.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameTimer } from "@/composables/useGameTimer";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { useRoundDraft } from "@/composables/useRoundDraft";
import { useSound } from "@/composables/useSound";
import { STORAGE_KEYS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const { play } = useSound();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();
const { leaveRoom } = useLeaveRoom();

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
const brokenImages = ref<Set<string>>(new Set());

const { timeLeft } = useGameTimer({
  startTime: () => store.guessingStartTime,
  duration: () => store.guessingTimeLimit,
  onExpire: () => autoSubmitGuesses(),
});

function avatarColorFor(playerId: string): string {
  const player = store.playersList.find((p) => p.id === playerId);
  return player?.color ?? getAvatarColor(playerId);
}

// Typed guesses are client-only until submitted, so they're drafted locally and
// restored on reconnect — mirroring the drawing-phase stroke recovery.
const draft = useRoundDraft<Record<string, string[]>>(STORAGE_KEYS.GUESSING_STATE, {
  round: () => store.currentRound,
  collect: () => playerGuesses.value,
  apply: (data) => {
    playerGuesses.value = data;
  },
  active: () => !allGuessesSubmitted.value,
});

onMounted(() => {
  submittedPlayers.value = [];
  if (!draft.restore() && assignedTargetPlayerId.value) {
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
  play("click");
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
    draft.clear();
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
  <div class="guessing-phase">
    <GameHeader :time-left="timeLeft" @leave="showLeaveDialog" />

    <div class="guessing-phase__body">
      <template v-if="assignedTargetPlayer">
        <!-- Drawing frame -->
        <HdCard class="drawing-frame">
          <h2 class="drawing-frame__title">
            <HdAvatar
              :initial="getAvatarInitial(assignedTargetPlayer.name)"
              :color="avatarColorFor(assignedTargetPlayer.id)"
              size="sm"
              :disconnected="!assignedTargetPlayer.connected"
            />
            {{ $t("guessing.guessPlayerDrawing", { name: assignedTargetPlayer.name }) }}
          </h2>
          <div class="drawing-frame__stage">
            <img
              v-if="assignedTargetPlayer.drawing && !brokenImages.has(assignedTargetPlayer.id)"
              :src="assignedTargetPlayer.drawing"
              :alt="$t('guessing.playerDrawingAlt')"
              class="drawing-frame__img"
              @error="handleImageError(assignedTargetPlayer.id)"
            >
            <p v-else-if="brokenImages.has(assignedTargetPlayer.id)" class="drawing-frame__placeholder">
              {{ $t("guessing.drawingFailed") }}
            </p>
            <p v-else class="drawing-frame__placeholder">{{ $t("guessing.waitingForDrawing") }}</p>
          </div>
        </HdCard>

        <!-- Guess panel -->
        <div class="guess-panel">
          <HdCard v-if="submittedPlayers.includes(assignedTargetPlayer.id)" variant="postit" class="guess-submitted">
            <svg
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
          </HdCard>

          <template v-else>
            <HdCard class="guess-card">
              <div class="guess-card__header">
                <h3 class="guess-card__title">{{ $t("guessing.yourGuesses") }}</h3>
                <HdPill variant="info">
                  {{ guessesFor(assignedTargetPlayer.id).filter((g) => g.trim()).length }}
                  / 10
                </HdPill>
              </div>
              <div class="guess-card__grid">
                <HdInput
                  v-for="(_, idx) in guessesFor(assignedTargetPlayer.id)"
                  :key="idx"
                  v-model="guessesFor(assignedTargetPlayer.id)[idx]"
                  class="guess-input"
                  :placeholder="$t('guessing.guessNumber', { number: idx + 1 })"
                  :aria-label="$t('guessing.guessNumber', { number: idx + 1 })"
                  @input="onGuessInput(assignedTargetPlayer.id, idx)"
                  @keydown="handleGuessKeydown(assignedTargetPlayer.id, idx, $event)"
                />
              </div>
              <HdButton
                variant="primary"
                class="guess-card__submit"
                @click="submitGuessesForPlayer(assignedTargetPlayer.id)"
              >
                {{ $t("guessing.submitGuesses") }}
              </HdButton>
            </HdCard>
            <HdCard variant="postit" class="guess-hint">{{ $t("guessing.hint") }}</HdCard>
          </template>
        </div>
      </template>

      <div v-else class="guessing-phase__waiting">
        <p>{{ $t("guessing.waitingForAssignedDrawing") }}</p>
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

    <HdDialog
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

<style scoped>
.guessing-phase {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  width: 100%;
  overflow: hidden;
  background: var(--color-paper);
}
.guessing-phase__body {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: var(--space-4);
  padding: var(--space-4);
  overflow: hidden;
}

/* Drawing frame */
.drawing-frame {
  display: flex;
  flex-direction: column;
  flex: 1.2;
  min-width: 0;
  min-height: 0;
}
.drawing-frame__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 2.5px solid var(--color-marker-red);
  font-size: var(--text-heading-sm);
}
.drawing-frame__stage {
  display: flex;
  flex: 1;
  min-height: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--r-input);
  background: var(--color-paper);
}
.drawing-frame__img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.drawing-frame__placeholder {
  font-style: italic;
  color: var(--color-ink-muted);
}

/* Guess panel */
.guess-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
}
.guess-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.guess-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}
.guess-card__title {
  margin: 0;
  font-size: var(--text-heading-sm);
}
.guess-card__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}
.guess-card__submit {
  width: 100%;
}
.guess-submitted {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 700;
}
.guess-submitted svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}
.guess-hint {
  font-size: var(--text-label-md);
}
.guessing-phase__waiting {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  font-style: italic;
  color: var(--color-ink-muted);
}

@media (max-width: 768px) {
  .guessing-phase__body {
    flex-direction: column;
    gap: var(--space-3);
    padding: var(--space-3);
    overflow-y: auto;
  }
  .drawing-frame {
    flex: none;
  }
  .drawing-frame__stage {
    height: min(155px, 26dvh);
  }
  .guess-card__grid {
    grid-template-columns: 1fr;
  }
}
</style>
