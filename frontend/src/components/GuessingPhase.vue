<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const { leaveRoom: _leaveRoom } = useLeaveRoom();

const playerGuesses = ref<Record<string, string[]>>({});
const submittedPlayers = ref<string[]>([]);
const allGuessesSubmitted = ref(false);
const leaveDialogRef = ref<HTMLDialogElement | null>(null);
const emptyGuessDialogTarget = ref<string | null>(null);
const emptyGuessDialogRef = ref<HTMLDialogElement | null>(null);
const timeLeft = ref(store.guessingTimeLimit);
const timerInterval = ref<number | null>(null);

const assignedTargetPlayerId = computed(() => store.guessTargets[store.localPlayerId] || null);
const assignedTargetPlayer = computed(() =>
  assignedTargetPlayerId.value ? store.playersList.find((p) => p.id === assignedTargetPlayerId.value) || null : null,
);
const currentScore = computed(() => store.localPlayer?.score || 0);
const brokenImages = ref<Set<string>>(new Set());

onMounted(() => {
  submittedPlayers.value = [];
  if (assignedTargetPlayerId.value) {
    playerGuesses.value[assignedTargetPlayerId.value] = [""];
  }
  startGuessingTimer();
});

onUnmounted(() => {
  stopTimer();
});

watch(
  () => store.guessingTimeLimit,
  (newGuessLength) => {
    const guessingStartTime = store.guessingStartTime;
    if (guessingStartTime && !Number.isNaN(guessingStartTime)) {
      const elapsed = Math.floor((Date.now() - guessingStartTime) / 1000);
      timeLeft.value = Math.max(0, newGuessLength - elapsed);
    } else {
      timeLeft.value = newGuessLength;
    }
  },
);

watch(
  () => store.guessingStartTime,
  () => {
    stopTimer();
    startGuessingTimer();
  },
);

function startGuessingTimer() {
  if (timerInterval.value) return;

  const updateTimeLeft = () => {
    const guessingStartTime = store.guessingStartTime;
    const guessingTimeLimit = store.guessingTimeLimit;

    if (guessingStartTime && !Number.isNaN(guessingStartTime)) {
      const elapsed = Math.floor((Date.now() - guessingStartTime) / 1000);
      timeLeft.value = elapsed < 0 || elapsed > guessingTimeLimit ? 0 : Math.max(0, guessingTimeLimit - elapsed);
      return;
    }

    timeLeft.value = guessingTimeLimit;
  };

  updateTimeLeft();
  timerInterval.value = window.setInterval(() => {
    updateTimeLeft();
    if (timeLeft.value <= 0) {
      stopTimer();
      autoSubmitGuesses();
    }
  }, 1000);
}

function stopTimer() {
  if (timerInterval.value) {
    clearInterval(timerInterval.value);
    timerInterval.value = null;
  }
}

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
    emptyGuessDialogRef.value?.showModal();
    return;
  }
  doSubmitGuesses(targetPlayerId, guesses);
}

function confirmSkipGuesses() {
  emptyGuessDialogRef.value?.close();
  const targetPlayerId = emptyGuessDialogTarget.value;
  emptyGuessDialogTarget.value = null;
  if (targetPlayerId) doSubmitGuesses(targetPlayerId, []);
}

function cancelSkipGuesses() {
  emptyGuessDialogRef.value?.close();
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
  leaveDialogRef.value?.showModal();
}

function cancelLeave() {
  leaveDialogRef.value?.close();
}

function confirmLeave() {
  leaveDialogRef.value?.close();
  _leaveRoom();
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

    <!-- Main content -->
    <div class="guessing-layout">
      <template v-if="assignedTargetPlayer">
        <!-- Drawing panel -->
        <div class="drawing-panel">
          <h2 class="panel-title">Guess {{ assignedTargetPlayer.name }}'s drawing</h2>
          <div class="drawing-display">
            <img
              v-if="assignedTargetPlayer.drawing && !brokenImages.has(assignedTargetPlayer.id)"
              :src="assignedTargetPlayer.drawing"
              alt="Player drawing"
              class="player-drawing"
              @error="handleImageError(assignedTargetPlayer.id)"
            >
            <p v-else-if="brokenImages.has(assignedTargetPlayer.id)" class="waiting-text">Drawing failed to load.</p>
            <p v-else class="waiting-text">Waiting for drawing…</p>
          </div>
        </div>

        <!-- Guessing panel -->
        <div class="guessing-panel">
          <div v-if="submittedPlayers.includes(assignedTargetPlayer.id)" class="submitted-banner">
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
            Guesses submitted! Waiting for others…
          </div>
          <div v-else class="guess-section">
            <h3 class="guess-heading">
              Your guesses
              <span class="guess-count"
                >{{ guessesFor(assignedTargetPlayer.id).filter(g => g.trim()).length }}
                / 10</span
              >
            </h3>
            <div class="guess-grid">
              <input
                v-for="(_, idx) in guessesFor(assignedTargetPlayer.id)"
                :key="idx"
                v-model="guessesFor(assignedTargetPlayer.id)[idx]"
                type="text"
                :placeholder="`Guess ${idx + 1}`"
                enterkeyhint="next"
                class="guess-input"
                @input="onGuessInput(assignedTargetPlayer.id, idx)"
                @keydown="handleGuessKeydown(assignedTargetPlayer.id, idx, $event)"
              >
            </div>
            <button type="button" class="btn-submit" @click="submitGuessesForPlayer(assignedTargetPlayer.id)">
              Submit Guesses
            </button>
          </div>
        </div>
      </template>

      <div v-else class="waiting-card">
        <p class="waiting-text">Waiting for your assigned drawing…</p>
      </div>
    </div>

    <!-- Leave confirmation dialog -->
    <dialog ref="leaveDialogRef" class="confirm-dialog" @click.self="cancelLeave">
      <h2>Leave Game?</h2>
      <p>Are you sure you want to leave?</p>
      <div class="dialog-actions">
        <button type="button" class="btn-dialog-cancel" @click="cancelLeave">Stay</button>
        <button type="button" class="btn-dialog-danger" @click="confirmLeave">Leave</button>
      </div>
    </dialog>

    <!-- Skip guesses confirmation dialog -->
    <dialog ref="emptyGuessDialogRef" class="confirm-dialog" @click.self="cancelSkipGuesses">
      <h2>No guesses entered</h2>
      <p>You haven't entered any guesses. Submit anyway?</p>
      <div class="dialog-actions">
        <button type="button" class="btn-dialog-cancel" @click="cancelSkipGuesses">Go back</button>
        <button type="button" class="btn-dialog-primary" @click="confirmSkipGuesses">Submit anyway</button>
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
  flex-shrink: 0;
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

.info-ready {
  color: rgba(255, 255, 255, 0.55);
  font-weight: 500;
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

/* ── Layout ────────────────────────────────────────────── */
.guessing-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
  gap: 1.25rem;
  padding: 1.25rem;
  overflow: hidden;
}

/* ── Drawing panel (left) ──────────────────────────────── */
.drawing-panel {
  flex: 1.2;
  min-width: 0;
  min-height: 0;
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-title {
  margin: 0 0 0.875rem;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text-dark);
  border-bottom: 2px solid var(--color-primary);
  padding-bottom: 0.5rem;
  flex-shrink: 0;
}

.drawing-display {
  flex: 1;
  min-height: 0;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  overflow: hidden;
}

.player-drawing {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

/* ── Guessing panel (right) ────────────────────────────── */
.guessing-panel {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.waiting-card {
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.8);
  font-size: 1.0625rem;
  width: 100%;
}

.waiting-text {
  color: var(--color-text-muted);
  font-style: italic;
}

/* ── Submitted banner ──────────────────────────────────── */
.submitted-banner {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 1rem 1.25rem;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: var(--radius-md);
  color: #155724;
  font-weight: 600;
  font-size: 1rem;
  align-self: flex-start;
  width: 100%;
}

/* ── Guess section ─────────────────────────────────────── */
.guess-section {
  background: white;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.submitted-banner-wrap {
  height: 100%;
  display: flex;
  align-items: flex-start;
}

.guess-heading {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.guess-count {
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-primary);
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.25);
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
  text-transform: none;
  letter-spacing: 0;
}

.guess-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

.guess-input {
  padding: 0.625rem 0.75rem;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  color: var(--color-text-dark);
  transition: border-color 0.15s;
}

.guess-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-shadow);
}

.btn-submit {
  padding: 0.75rem;
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.btn-submit:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}

/* ── Dialogs ───────────────────────────────────────────── */
.confirm-dialog {
  border: none;
  border-radius: var(--radius-lg);
  padding: 2rem;
  max-width: 360px;
  width: calc(100% - 2rem);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  margin: 0;
}

.confirm-dialog[open] {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.confirm-dialog::backdrop {
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
}

.confirm-dialog h2 {
  margin: 0 0 0.625rem;
  font-size: 1.25rem;
  color: var(--color-text-dark);
}

.confirm-dialog p {
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

.btn-dialog-primary {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%);
  border: none;
  color: white;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: filter 0.15s;
}

.btn-dialog-primary:hover {
  filter: brightness(1.08);
}

/* ── Mobile ────────────────────────────────────────────── */
@media (max-width: 768px) {
  .game-header {
    grid-template-columns: 1fr auto 1fr;
    padding: 0.5rem 0.875rem;
    gap: 0.5rem;
  }

  .timer {
    font-size: 1.5rem;
    padding: 0.25rem 0.75rem;
    min-width: 3rem;
  }

  /* Drawing fixed at top, guesses scroll below */
  .guessing-layout {
    flex-direction: column;
    padding: 0.75rem;
    gap: 0.75rem;
    overflow: hidden;
  }

  .drawing-panel {
    flex: 0 0 auto;
    padding: 0.875rem;
  }

  .drawing-display {
    flex: none;
    height: min(155px, 26dvh);
  }

  .guessing-panel {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
  }

  .guess-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .game-header {
    padding: 0.4rem 0.625rem;
    gap: 0.35rem;
  }

  .btn-leave {
    padding: 0.35rem 0.6rem;
    font-size: 0.75rem;
  }

  .timer {
    font-size: 1.25rem;
    padding: 0.2rem 0.6rem;
  }
}
</style>
