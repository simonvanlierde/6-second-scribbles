<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import { useDrawingCanvas } from '@/composables/useDrawingCanvas'
import { clearGameEngine } from '@/composables/gameEngineInstance'

const store = useGameStore()
const router = useRouter()
const { send, disconnect } = useGameConnection()
const canvas = useDrawingCanvas()

const canvasElement = ref<HTMLCanvasElement | null>(null)
const timeLeft = ref(store.roundLength) // Initialize directly with server-provided roundLength
const timerInterval = ref<number | null>(null)

// Track guesses per player
const playerGuesses = ref<Record<string, string[]>>({})
const submittedPlayers = ref<Set<string>>(new Set())
const allGuessesSubmitted = ref(false)

// Use game phase from store
const gamePhase = computed(() => store.gamePhase)

const category = computed(() => store.localPlayerCard?.category || 'Loading...')
const items = computed(() => store.localPlayerCard?.items || [])
const currentScore = computed(() => store.localPlayer?.score || 0)
const otherPlayers = computed(() => store.playersList.filter((p) => p.id !== store.localPlayerId))

onMounted(() => {
  // Don't restore from localStorage - the card is already set by store.startRound()
  // Only restore if we're in the middle of a drawing phase and have no current card
  if (gamePhase.value === 'drawing' && !store.localPlayerCard) {
    const savedState = localStorage.getItem('gameState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      store.localPlayerCard = parsedState.localPlayerCard
      canvas.loadDrawing(parsedState.drawing)
    }
  }

  if (canvasElement.value) {
    canvas.initCanvas(canvasElement.value)
    if (gamePhase.value === 'drawing') {
      startDrawingTimer()
    }
  }

  // Initialize guess arrays for all other players
  submittedPlayers.value.clear()
  otherPlayers.value.forEach((player) => {
    playerGuesses.value[player.id] = Array(10).fill('')
  })
})

onUnmounted(() => {
  // Save game state to local storage
  const gameState = {
    localPlayerCard: store.localPlayerCard,
    drawing: canvas.toDataURL(),
  }
  localStorage.setItem('gameState', JSON.stringify(gameState))

  stopTimer()
})

// Watch for phase changes to drawing phase to restart timer
watch(
  () => store.gamePhase,
  async (newPhase, oldPhase) => {
    if (newPhase === 'drawing' && oldPhase !== 'drawing') {
      // Wait for the next tick to ensure the canvas element is rendered
      await new Promise((resolve) => setTimeout(resolve, 0))

      // Ensure canvas is initialized with the current element
      if (canvasElement.value) {
        canvas.initCanvas(canvasElement.value)
      }

      // Clear canvas for new round
      if (canvas.canvasRef.value) {
        canvas.clear()
      }

      // Restart timer for new round
      stopTimer()
      startDrawingTimer()

      // Reinitialize guess arrays for all other players
      playerGuesses.value = {}
      submittedPlayers.value.clear()
      otherPlayers.value.forEach((player) => {
        playerGuesses.value[player.id] = Array(10).fill('')
      })
    }
  },
  { immediate: true }
)

// Watch for changes in store.roundLength and recalculate timeLeft
watch(
  () => store.roundLength,
  (newRoundLength) => {
    timeLeft.value = newRoundLength
  }
)

function startDrawingTimer() {
  if (timerInterval.value) {
    console.warn('Timer is already running. Skipping start.')
    return
  }

  const roundLength = store.roundLength // Always use server-provided roundLength
  const roundStartTime = store.roundStartTime // Use server-provided roundStartTime

  if (roundStartTime && !isNaN(roundStartTime)) {
    const elapsed = Math.floor((Date.now() - roundStartTime) / 1000)
    console.log('[Timer] Calculated elapsed time:', elapsed, 'roundStartTime:', roundStartTime)

    if (elapsed < 0 || elapsed > roundLength) {
      console.warn('[Timer] Invalid elapsed time. Defaulting timeLeft to roundLength.')
      timeLeft.value = roundLength
    } else {
      timeLeft.value = Math.max(0, roundLength - elapsed)
    }
  } else {
    console.warn(
      '[Timer] roundStartTime is invalid or not set. Defaulting timeLeft to roundLength.'
    )
    timeLeft.value = roundLength
  }

  timerInterval.value = window.setInterval(() => {
    if (roundStartTime && !isNaN(roundStartTime)) {
      const elapsed = Math.floor((Date.now() - roundStartTime) / 1000)
      timeLeft.value = Math.max(0, roundLength - elapsed)
    } else {
      timeLeft.value = roundLength
    }

    if (timeLeft.value <= 0) {
      stopTimer()
      endDrawingPhase()
    }
  }, 1000)
}

function stopTimer() {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
}

function endDrawingPhase() {
  if (store.gamePhase !== 'drawing') {
    console.warn('[endDrawingPhase] Game phase is not "drawing". Skipping.')
    return
  }

  // Send drawing to server
  const drawing = canvas.toDataURL()
  console.log('[endDrawingPhase] Sending drawing_complete message')
  send({
    type: 'drawing_complete',
    playerId: store.localPlayerId,
    drawing,
  })

  // Send player_ready message to indicate drawing completion
  send({
    type: 'player_ready',
    playerId: store.localPlayerId,
  })

  // Clear saved state after the drawing phase ends
  localStorage.removeItem('gameState')

  // Game phase will be updated by server via start_guessing message
}

function leaveRoom() {
  // Gracefully disconnect and return to lobby
  stopTimer()
  disconnect()
  clearGameEngine()
  store.reset()
  router.push('/')
}

function handleColorChange(event: Event) {
  const target = event.target as HTMLInputElement
  canvas.setColor(target.value)
}

function handleBrushSizeChange(event: Event) {
  const target = event.target as HTMLInputElement
  canvas.setWidth(Number(target.value))
}

function clearCanvas() {
  canvas.clear()
}

function submitGuessesForPlayer(targetPlayerId: string) {
  const guesses = playerGuesses.value[targetPlayerId] || []
  const filteredGuesses = guesses.filter((g) => g.trim() !== '')

  if (filteredGuesses.length === 0) return

  send({
    type: 'submit_guess',
    playerId: store.localPlayerId,
    targetPlayerId: targetPlayerId,
    guesses: filteredGuesses,
  })

  // Mark this player as submitted
  submittedPlayers.value.add(targetPlayerId)

  // Check if all guesses are submitted
  if (submittedPlayers.value.size === otherPlayers.value.length) {
    allGuessesSubmitted.value = true
    // Send player_ready message to indicate completion
    send({
      type: 'player_ready',
      playerId: store.localPlayerId,
    })
  }
}
</script>

<template>
  <div v-if="gamePhase === 'drawing'" class="game-screen">
    <div class="game-header">
      <div class="round-info">Round {{ store.currentRound }} of {{ store.maxRounds }}</div>
      <div class="timer" :class="{ warning: timeLeft <= 10 }">{{ timeLeft }}</div>
      <div class="score">Score: {{ currentScore }}</div>
      <button class="btn btn-secondary btn-leave" @click="leaveRoom">🚪 Leave</button>
    </div>

    <!-- Ready status for drawing phase -->
    <div class="ready-status-header" v-if="store.readyCount > 0">
      <p class="ready-count-small">
        {{ store.readyCount }} / {{ store.totalPlayers }} players finished drawing
      </p>
    </div>

    <div class="drawing-container">
      <div class="category-card">
        <h3>{{ category }}</h3>
        <ul class="items-list">
          <li v-for="(item, index) in items" :key="index">{{ item }}</li>
        </ul>
      </div>

      <div class="canvas-container">
        <div class="canvas-tools">
          <div class="tool-group">
            <label>Color:</label>
            <input type="color" :value="canvas.currentColor.value" @input="handleColorChange" />
          </div>
          <div class="tool-group">
            <label>Size:</label>
            <input
              type="range"
              min="1"
              max="10"
              :value="canvas.currentWidth.value"
              @input="handleBrushSizeChange"
            />
          </div>
          <button class="btn btn-small" @click="clearCanvas">Clear</button>
        </div>
        <canvas ref="canvasElement" class="drawing-canvas"></canvas>
      </div>
    </div>
  </div>

  <div v-else-if="gamePhase === 'guessing'" class="guessing-screen">
    <div class="container">
      <h2>Guess what others drew!</h2>
      <p class="info-text">Look at each player's drawing and guess what they drew</p>

      <!-- Ready status display -->
      <div class="ready-status">
        <p class="ready-count">
          {{ store.readyCount }} / {{ store.totalPlayers }} players finished guessing
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
            <button class="btn btn-primary" @click="submitGuessesForPlayer(player.id)">
              Submit Guesses for {{ player.name }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="waiting-screen">
    <div class="container">
      <h2>Waiting for round to start...</h2>
    </div>
  </div>
</template>

<style scoped>
.game-screen {
  width: 100%;
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

.ready-status-header {
  padding: 0.5rem 2rem;
  background-color: #e7f3ff;
  text-align: center;
}

.ready-count-small {
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  margin: 0;
}

.round-info {
  font-size: 1.125rem;
  font-weight: 500;
}

.timer {
  font-size: 2rem;
  font-weight: bold;
  padding: 0.5rem 1.5rem;
  background-color: #3498db;
  border-radius: 8px;
  min-width: 100px;
  text-align: center;
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

.score {
  font-size: 1.125rem;
  font-weight: 500;
}

.drawing-container {
  display: flex;
  gap: 2rem;
  padding: 2rem;
  flex: 1;
}

.category-card {
  flex: 0 0 300px;
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: fit-content;
}

.category-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.5rem;
}

.items-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.items-list li {
  padding: 0.5rem;
  margin: 0.25rem 0;
  background-color: #f8f9fa;
  border-radius: 4px;
  font-size: 0.875rem;
}

.canvas-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 1rem;
}

.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #dee2e6;
  align-items: center;
}

.tool-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.tool-group label {
  font-weight: 500;
  font-size: 0.875rem;
}

.drawing-canvas {
  flex: 1;
  border: 2px solid #dee2e6;
  border-radius: 4px;
  cursor: crosshair;
  background: white;
  width: 100%;
  min-height: 400px;
}

.guessing-screen {
  padding: 2rem;
  min-height: 100vh;
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
  background-color: #f8f9fa;
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

.drawing-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
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
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
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

.waiting-screen {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

@media (max-width: 768px) {
  .game-header {
    padding: 0.75rem 1rem;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .round-info,
  .score {
    font-size: 0.875rem;
  }

  .timer {
    font-size: 1.5rem;
    padding: 0.375rem 1rem;
    min-width: 80px;
  }

  .btn-leave {
    padding: 0.375rem 0.75rem;
    font-size: 0.875rem;
  }

  .drawing-container {
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
  }

  .category-card {
    flex: 0 0 auto;
    padding: 1rem;
  }

  .category-card h3 {
    font-size: 1.25rem;
  }

  .canvas-container {
    padding: 0.75rem;
  }

  .canvas-tools {
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .tool-group {
    font-size: 0.875rem;
  }

  .drawing-canvas {
    min-height: 300px;
    /* Ensure canvas takes full width on mobile */
    touch-action: none;
    /* Prevent default touch actions for better drawing */
  }

  .guess-grid {
    grid-template-columns: 1fr;
  }

  .guessing-screen {
    padding: 1rem;
  }

  .drawing-card {
    padding: 1rem;
  }

  .drawing-display {
    min-height: 200px;
  }
}

/* Extra small devices (phones in portrait) */
@media (max-width: 480px) {
  .game-header {
    font-size: 0.875rem;
  }

  .timer {
    font-size: 1.25rem;
    padding: 0.25rem 0.75rem;
    min-width: 60px;
  }

  .drawing-container {
    padding: 0.5rem;
  }

  .category-card {
    padding: 0.75rem;
  }

  .items-list li {
    font-size: 0.75rem;
    padding: 0.375rem;
  }

  .drawing-canvas {
    min-height: 250px;
  }

  .canvas-tools {
    font-size: 0.75rem;
  }

  .guess-input {
    padding: 0.5rem;
    font-size: 0.875rem;
  }
}
</style>
