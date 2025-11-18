<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { watch } from 'vue'
import { useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import { useLeaveRoom } from '@/composables/useLeaveRoom'
import useGuesses from '@/composables/useGuesses'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const router = useRouter()
const store = useGameStore()
const { send } = useGameConnection()
const { leave: leaveRoom } = useLeaveRoom()
const showLeaveDialog = ref(false)

const otherPlayers = computed(() => store.playersList.filter((p) => p.id !== store.localPlayerId))
const { playerGuesses, submittedPlayers, init, submitGuesses } = useGuesses(
  otherPlayers.value.map((p) => p.id)
)

onMounted(() => {
  init()
})

// Re-init guesses if the list of other players changes (join/leave)
watch(otherPlayers, () => {
  init()
})

function submitGuessesForPlayer(targetPlayerId: string) {
  const filtered = submitGuesses(targetPlayerId)
  if (!filtered) return

  send({
    type: 'submit_guess',
    playerId: store.localPlayerId,
    targetPlayerId,
    guesses: filtered,
  })

  if (submittedPlayers.value.size === otherPlayers.value.length) {
    send({ type: 'player_ready', playerId: store.localPlayerId })
  }
}

function confirmLeave() {
  // perform leave via centralized handler
  leaveRoom()
}
</script>

<template>
  <div class="guessing-screen">
    <div class="game-header">
      <button class="btn-leave-small" @click="showLeaveDialog = true" title="Leave Game">
        🚪←
      </button>
      <h2 style="margin: 0">Guess what others drew!</h2>
      <div class="score">Score: {{ store.localPlayer?.score || 0 }}</div>
    </div>
    <div class="container">
      <p class="info-text">Look at each player's drawing and guess what they drew</p>

      <div class="ready-status">
        <p class="ready-count">
          {{ submittedPlayers.size }} / {{ otherPlayers.length + 1 }} players finished guessing
        </p>
      </div>

      <div class="players-drawings">
        <div v-for="player in otherPlayers" :key="player.id" class="drawing-card">
          <h3>{{ player.name }}'s Drawing</h3>
          <div class="drawing-display">
            <img
              v-if="player.drawing"
              :src="player.drawing"
              alt="Player drawing"
              class="player-drawing"
            />
            <p v-else class="waiting-text">Waiting for drawing...</p>
          </div>
          <div v-if="submittedPlayers.has(player.id)" class="submitted-message">
            <p>✓ Guesses submitted! Waiting for other players...</p>
          </div>
          <div v-else class="guess-inputs">
            <h4>Your guesses (up to 10):</h4>
            <div class="guess-grid">
              <input
                v-for="index in 10"
                :key="index"
                v-model="
                  (playerGuesses[player.id] = playerGuesses[player.id] || Array(10).fill(''))[
                    index - 1
                  ]
                "
                type="text"
                :placeholder="`Guess ${index}`"
                class="guess-input"
              />
            </div>
            <button
              class="btn btn-primary"
              @click="submitGuessesForPlayer(player.id)"
              :disabled="submittedPlayers.has(player.id)"
            >
              Submit guesses
            </button>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-model="showLeaveDialog"
      title="Leave Game?"
      message="Are you sure you want to leave? Your progress will be lost."
      confirmText="Leave"
      cancelText="Stay"
      @confirm="confirmLeave"
    />
  </div>
</template>

<style scoped>
.guessing-screen {
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
.container {
  padding: 2rem;
  flex: 1;
}
.info-text {
  text-align: center;
  color: #6c757d;
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
  background: #f8f9fa;
  border-radius: 4px;
  display: inline-block;
}
.players-drawings {
  display: grid;
  gap: 2rem;
}
.drawing-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.drawing-display {
  margin-bottom: 1.5rem;
  border: 2px solid #dee2e6;
  border-radius: 4px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f8f9fa;
}
.player-drawing {
  max-width: 100%;
  max-height: 400px;
  object-fit: contain;
}
.waiting-text {
  color: #6c757d;
  font-style: italic;
}
.guess-inputs {
  max-width: 100%;
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
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}
.submitted-message {
  padding: 2rem;
  text-align: center;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 4px;
  color: #155724;
}

.btn-leave-small {
  padding: 0.375rem 0.5rem;
  background-color: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: white;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  opacity: 0.8;
}

.btn-leave-small:hover {
  background-color: rgba(255, 255, 255, 0.25);
  opacity: 1;
  transform: scale(1.05);
}
</style>
