<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

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
const brokenImages = ref<Set<string>>(new Set());

onMounted(() => {
  submittedPlayers.value = [];
  if (assignedTargetPlayerId.value) {
    playerGuesses.value[assignedTargetPlayerId.value] = Array(10).fill("");
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
  if (!playerGuesses.value[playerId]) playerGuesses.value[playerId] = Array(10).fill("");
  return playerGuesses.value[playerId] as string[];
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

function showLeaveConfirmation() {
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
  <div class="guessing-screen">
    <div class="container">
      <div class="guessing-header">
        <h2>Guess what others drew!</h2>
        <div class="header-actions">
          <div class="timer" :class="{ warning: timeLeft <= 10 }">{{ timeLeft }}</div>
          <button type="button" class="btn btn-secondary btn-leave" @click="showLeaveConfirmation">🚪 Leave</button>
        </div>
      </div>
      <p class="info-text">Look at each player's drawing and guess what they drew before the timer runs out</p>

      <div class="ready-status">
        <p class="ready-count">{{ store.readyCount }} / {{ store.totalPlayers }} players finished guessing</p>
      </div>

      <div class="players-drawings">
        <div v-if="assignedTargetPlayer" class="drawing-card">
          <h3>{{ assignedTargetPlayer.name }}'s Drawing</h3>
          <div class="drawing-display">
            <img
              v-if="assignedTargetPlayer.drawing && !brokenImages.has(assignedTargetPlayer.id)"
              :src="assignedTargetPlayer.drawing"
              alt="Player drawing"
              class="player-drawing"
              @error="handleImageError(assignedTargetPlayer.id)"
            >
            <p v-else-if="brokenImages.has(assignedTargetPlayer.id)" class="waiting-text">Drawing failed to load.</p>
            <p v-else class="waiting-text">Waiting for drawing...</p>
          </div>

          <div v-if="submittedPlayers.includes(assignedTargetPlayer.id)" class="submitted-message">
            <p>✓ Guesses submitted! Waiting for other players...</p>
          </div>
          <div v-else class="guess-inputs">
            <h4>Your guesses (up to 10):</h4>
            <div class="guess-grid">
              <input
                v-for="index in 10"
                :key="index"
                v-model="guessesFor(assignedTargetPlayer.id)[index - 1]"
                type="text"
                :placeholder="`Guess ${index}`"
                class="guess-input"
              >
            </div>
            <button type="button" class="btn btn-primary" @click="submitGuessesForPlayer(assignedTargetPlayer.id)">
              Submit Guesses for {{ assignedTargetPlayer.name }}
            </button>
          </div>
        </div>
        <p v-else class="waiting-text">Waiting for your assigned drawing...</p>
      </div>
    </div>

    <!-- Leave confirmation dialog -->
    <dialog ref="leaveDialogRef" class="confirm-dialog" @click.self="cancelLeave">
      <h2>Leave Room?</h2>
      <p>Are you sure you want to leave this room?</p>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" @click="cancelLeave">Cancel</button>
        <button type="button" class="btn btn-danger" @click="confirmLeave">Leave</button>
      </div>
    </dialog>

    <!-- Skip guesses confirmation dialog -->
    <dialog ref="emptyGuessDialogRef" class="confirm-dialog" @click.self="cancelSkipGuesses">
      <h2>Submit with no guesses?</h2>
      <p>You haven't entered any guesses. Submit anyway?</p>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" @click="cancelSkipGuesses">Go back</button>
        <button type="button" class="btn btn-primary" @click="confirmSkipGuesses">Submit anyway</button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.guessing-screen {
  padding: 2rem;
  min-height: 100vh;
}

.guessing-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.guessing-header h2 {
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.timer {
  font-size: 2rem;
  font-weight: bold;
  padding: 0.5rem 1.5rem;
  background-color: #3498db;
  border-radius: var(--radius-md);
  min-width: 100px;
  text-align: center;
  color: white;
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

.confirm-dialog {
  border: none;
  border-radius: var(--radius-md);
  padding: 2rem;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.confirm-dialog::backdrop {
  background-color: rgba(0, 0, 0, 0.5);
}

.confirm-dialog h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-text);
}

.confirm-dialog p {
  margin-bottom: 1.5rem;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-danger {
  background-color: var(--color-danger);
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

.info-text {
  text-align: center;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

.ready-status {
  margin: 1rem 0 2rem 0;
  text-align: center;
}

.ready-count {
  font-size: 1.125rem;
  font-weight: 600;
  color: #495057;
  margin: 0;
  padding: 0.75rem;
  background-color: var(--color-surface);
  border-radius: 4px;
  display: inline-block;
}

.players-drawings {
  display: grid;
  gap: 2rem;
}

.drawing-card {
  background: white;
  border-radius: var(--radius-md);
  padding: 1.5rem;
  box-shadow: var(--shadow-sm);
}

.drawing-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
}

.drawing-display {
  margin-bottom: 1.5rem;
  border: 2px solid var(--color-border);
  border-radius: 4px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
}

.player-drawing {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}

.waiting-text {
  color: var(--color-text-muted);
  font-style: italic;
}

.guess-inputs {
  max-width: 100%;
}

.guess-inputs h4 {
  margin-bottom: 1rem;
  color: #495057;
  font-size: 1rem;
}

.guess-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.guess-input {
  padding: 0.75rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
}

.guess-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-shadow);
}

.submitted-message {
  padding: 2rem;
  text-align: center;
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  color: #155724;
}

.submitted-message p {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 500;
}

@media (max-width: 768px) {
  .guessing-screen {
    padding: 1rem;
  }

  .drawing-card {
    padding: 1rem;
  }

  .drawing-display {
    min-height: 200px;
  }

  .guess-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .guess-input {
    padding: 0.5rem;
    font-size: 0.875rem;
  }
}
</style>
