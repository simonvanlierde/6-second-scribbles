<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import { useLeaveRoom } from '@/composables/useLeaveRoom'
import GameDrawpad from '@/components/GameDrawpad.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import useRoundTimer from '@/composables/useRoundTimer'

const router = useRouter()
const store = useGameStore()
const { send } = useGameConnection()
const { leave: leaveRoom } = useLeaveRoom()

const gamePad = ref<InstanceType<typeof GameDrawpad> | null>(null)
const showLeaveDialog = ref(false)
const { timeLeft, start, stop } = useRoundTimer({
  roundLength: store.roundLength,
  roundStartTime: store.roundStartTime,
})

const category = computed(() => store.localPlayerCard?.category || 'Loading...')
const items = computed(() => store.localPlayerCard?.items || [])

onMounted(() => {
  // Restore drawing if necessary (only if round started and local card missing)
  if (store.gamePhase === 'drawing' && !store.localPlayerCard) {
    const savedState = localStorage.getItem('gameState')
    if (savedState) {
      const parsedState = JSON.parse(savedState)
      store.localPlayerCard = parsedState.localPlayerCard
      if (gamePad.value && typeof gamePad.value.loadDrawing === 'function') {
        gamePad.value.loadDrawing(parsedState.drawing)
      }
    }
  }
})

onUnmounted(() => {
  // Save game state to local storage (drawing)
  const drawing =
    gamePad.value && typeof gamePad.value.toDataURL === 'function' ? gamePad.value.toDataURL() : ''
  const gameState = {
    localPlayerCard: store.localPlayerCard,
    drawing,
  }
  localStorage.setItem('gameState', JSON.stringify(gameState))

  stop()
})

function startDrawingTimer() {
  start()
}

function stopTimer() {
  stop()
}

function endDrawingPhase() {
  if (store.gamePhase !== 'drawing') return

  const drawing =
    gamePad.value && typeof gamePad.value.toDataURL === 'function' ? gamePad.value.toDataURL() : ''
  send({
    type: 'drawing_complete',
    playerId: store.localPlayerId,
    drawing,
  })

  send({ type: 'player_ready', playerId: store.localPlayerId })
  localStorage.removeItem('gameState')
}

// Watchers: restart timer when entering drawing phase
watch(
  () => store.gamePhase,
  (newPhase, oldPhase) => {
    if (newPhase === 'drawing' && oldPhase !== 'drawing') {
      // Clear and start timer
      stopTimer()
      startDrawingTimer()
    }
  },
  { immediate: true }
)

// If the timer reaches zero while in drawing, end the drawing phase automatically
watch(timeLeft, (val: number) => {
  if (val <= 0) endDrawingPhase()
})

function confirmLeave() {
  stop()
  // leaveRoom will handle disconnect/clear engine, navigate then reset store
  leaveRoom()
}
</script>

<template>
  <div class="game-screen">
    <div class="game-header">
      <div style="display: flex; gap: 1rem; align-items: center">
        <button class="btn-leave-small" @click="showLeaveDialog = true" title="Leave Game">
          🚪←
        </button>
        <div class="round-info">Round {{ store.currentRound }} of {{ store.maxRounds }}</div>
      </div>
      <div class="timer" :class="{ warning: timeLeft <= 10 }">{{ timeLeft }}</div>

      <div class="score">Score: {{ store.localPlayer?.score || 0 }}</div>
    </div>

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
        <GameDrawpad ref="gamePad" mode="large" />
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
.items-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.items-list li {
  padding: 0.5rem;
  margin: 0.25rem 0;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 0.875rem;
}
.canvas-container {
  flex: 1;
  display: flex;
  flex-direction: column;
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
