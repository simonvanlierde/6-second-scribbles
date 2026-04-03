<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { injectGameEngine } from "@/composables/injectionKeys";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const gameEngineRef = injectGameEngine();
const { leaveRoom: _leaveRoom } = useLeaveRoom(gameEngineRef);

const playerGuesses = ref<Record<string, string[]>>({});
const submittedPlayers = ref<string[]>([]);
const allGuessesSubmitted = ref(false);
const leaveDialogRef = ref<HTMLDialogElement | null>(null);
const emptyGuessDialogTarget = ref<string | null>(null);
const emptyGuessDialogRef = ref<HTMLDialogElement | null>(null);

const otherPlayers = computed(() => store.playersList.filter((p) => p.id !== store.localPlayerId));

onMounted(() => {
  submittedPlayers.value = [];
  for (const player of otherPlayers.value) {
    playerGuesses.value[player.id] = Array(10).fill("");
  }
});

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

  if (submittedPlayers.value.length === otherPlayers.value.length) {
    allGuessesSubmitted.value = true;
    send({ type: "player_ready", playerId: store.localPlayerId });
  }
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
        <button type="button" class="btn btn-secondary btn-leave" @click="showLeaveConfirmation">🚪 Leave</button>
      </div>
      <p class="info-text">Look at each player's drawing and guess what they drew</p>

      <div class="ready-status">
        <p class="ready-count">{{ store.readyCount }} / {{ store.totalPlayers }} players finished guessing</p>
      </div>

      <div class="players-drawings">
        <div v-for="player in otherPlayers" :key="player.id" class="drawing-card">
          <h3>{{ player.name }}'s Drawing</h3>
          <div class="drawing-display">
            <img v-if="player.drawing" :src="player.drawing" alt="Player drawing" class="player-drawing">
            <p v-else class="waiting-text">Waiting for drawing...</p>
          </div>

          <div v-if="submittedPlayers.includes(player.id)" class="submitted-message">
            <p>✓ Guesses submitted! Waiting for other players...</p>
          </div>
          <div v-else class="guess-inputs">
            <h4>Your guesses (up to 10):</h4>
            <div class="guess-grid">
              <input
                v-for="index in 10"
                :key="index"
                v-model="guessesFor(player.id)[index - 1]"
                type="text"
                :placeholder="`Guess ${index}`"
                class="guess-input"
              >
            </div>
            <button type="button" class="btn btn-primary" @click="submitGuessesForPlayer(player.id)">
              Submit Guesses for {{ player.name }}
            </button>
          </div>
        </div>
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
