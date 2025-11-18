<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import { useLeaveRoom } from '@/composables/useLeaveRoom'
import logger from '@/utils/logger'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import computeDenseRanks from '@/utils/ranking'
import type { PlayerScore, RankedItem } from '@/utils/ranking'

const router = useRouter()
const store = useGameStore()
const { send } = useGameConnection()
const { leave: leaveRoom } = useLeaveRoom()
const isReady = ref(false)
const autoRestartTimeout = ref<number | null>(null)
const showLeaveDialog = ref(false)

const finalScores = computed<PlayerScore[]>(() => store.getFinalScores())

// Use shared ranking util (dense ranking)
const rankedScores = computed<RankedItem[]>(() => computeDenseRanks(finalScores.value))

// Compute winners (could be multiple when tied for top score)
const winners = computed<PlayerScore[]>(() => {
  if (!rankedScores.value.length) return []
  const first = rankedScores.value[0]
  if (!first) return []
  const topRank = first.rank
  return rankedScores.value.filter((r) => r.rank === topRank).map((r) => r.player)
})

const winner = computed<PlayerScore | null>(() => (winners.value[0] ?? null) as PlayerScore | null)

// Watch for game phase changes (when host starts new game)
watch(
  () => store.gamePhase,
  (newPhase) => {
    if (newPhase === 'waiting-room') {
      // Host started a new game, redirect to waiting room
      clearAutoRestartTimeout()
      router.push(`/room/${store.roomCode}`)
    }
  }
)

// Watch for all players ready - host initiates auto-restart after 60s
watch(
  () => store.readyCount,
  (newReadyCount) => {
    // Only host handles auto-restart
    if (!store.isHost) return

    // Check if all players are ready
    if (newReadyCount > 0 && newReadyCount === store.totalPlayers) {
      logger.info('[FinalResultsView] All players ready. Auto-restart in 60 seconds.')

      // Set timeout for auto-restart
      clearAutoRestartTimeout()
      autoRestartTimeout.value = window.setTimeout(() => {
        logger.info('[FinalResultsView] Auto-restart timeout reached. Restarting game.')
        playAgain()
      }, 60000) // 60 seconds
    }
  }
)

function clearAutoRestartTimeout() {
  if (autoRestartTimeout.value) {
    clearTimeout(autoRestartTimeout.value)
    autoRestartTimeout.value = null
  }
}

function playAgain() {
  if (store.isHost) {
    // Host broadcasts restart_game message to all players (including themselves)
    send({
      type: 'restart_game',
    })
    // Server will handle phase change and broadcast - watcher will navigate
  } else {
    // Non-host indicates they're ready to play again
    isReady.value = true
    send({
      type: 'player_ready',
      playerId: store.localPlayerId,
    })
  }
}

function confirmLeaveRoom() {
  // Disconnect and go back to lobby
  clearAutoRestartTimeout()
  // centralized leave handles disconnect, clearing engine, navigate then reset
  leaveRoom()
}

onUnmounted(() => {
  clearAutoRestartTimeout()
})
</script>

<template>
  <div class="screen">
    <div class="container">
      <h1>🏆 Game Over!</h1>

      <div class="card winner-card">
        <div class="trophy-icon"><font-awesome-icon icon="fa-solid fa-trophy" /></div>
        <h2>
          Winner:
          <template v-if="winners.length > 1">
            <!-- Show multiple winners joined by commas -->
            <span class="multi-winners">{{ winners.map((w) => w.playerName).join(', ') }}</span>
          </template>
          <template v-else>
            {{ winner?.playerName || 'Unknown' }}
          </template>
        </h2>
        <p class="winner-score">
          <!-- Show top score if present -->
          {{ winners[0]?.score ?? 0 }} points
        </p>
        <p v-if="winners.length > 1" class="tie-note">It's a tie!</p>
      </div>

      <div class="card">
        <h2>Final Scores</h2>
        <div class="scores-list">
          <div
            v-for="(item, index) in rankedScores"
            :key="item.player.playerId"
            class="score-item"
            :class="{
              winner: item.rank === 1,
              'current-player': item.player.playerId === store.localPlayerId,
            }"
          >
            <div class="rank">
              {{ item.rank }}
              <span v-if="item.tiedWithPrevious" class="tie-badge">
                <font-awesome-icon icon="fa-solid fa-equals" class="tie-icon" />
              </span>
            </div>
            <div class="player-info">
              <span class="player-name">{{ item.player.playerName }}</span>
              <span v-if="item.player.playerId === store.localPlayerId" class="player-badge"
                >(You)</span
              >
            </div>
            <div class="player-score">{{ item.player.score }} pts</div>
          </div>
        </div>

        <!-- Ready status display for all players -->
        <div class="ready-status">
          <p class="ready-count">{{ store.readyCount }} / {{ store.totalPlayers }} players ready</p>
        </div>

        <div class="button-group">
          <button v-if="store.isHost" class="btn btn-primary" @click="playAgain">
            🔄 Play Again
          </button>
          <button v-else-if="!isReady" class="btn btn-primary" @click="playAgain">
            ✓ Ready for Next Game
          </button>
          <div v-else class="ready-indicator">✓ Ready! Waiting for host to start new game...</div>
          <button class="btn btn-to-lobby" @click="showLeaveDialog = true">→🚪 Leave room</button>
        </div>
      </div>

      <div class="card stats-card">
        <h3>Game Statistics</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">Total Rounds</div>
            <div class="stat-value">{{ store.maxRounds }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Players</div>
            <div class="stat-value">{{ store.playersList.length }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">Difficulty</div>
            <div class="stat-value">{{ store.difficulty }}</div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-model="showLeaveDialog"
      title="Leave to Lobby?"
      message="Are you sure you want to leave? You will return to the lobby."
      confirmText="Leave"
      cancelText="Stay"
      @confirm="confirmLeaveRoom"
    />
  </div>
</template>

<style scoped>
.winner-card {
  text-align: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  margin-bottom: 2rem;
}

.trophy-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  animation: bounce 1s infinite;
}

@keyframes bounce {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.winner-card h2 {
  margin: 0.5rem 0;
  font-size: 2rem;
}

.winner-score {
  font-size: 1.5rem;
  font-weight: bold;
  margin: 0;
}

.tie-note {
  margin-top: 0.5rem;
  font-style: italic;
  opacity: 0.95;
}

.tie-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 0.5rem;
  background-color: rgba(255, 255, 255, 0.15);
  color: white;
  border-radius: 999px;
  padding: 0.125rem 0.35rem;
  font-weight: 700;
}

.tie-icon {
  width: 0.9rem;
  height: 0.9rem;
}

.winner-card .multi-winners {
  font-size: 1rem;
  opacity: 0.95;
}

.scores-list {
  margin: 1.5rem 0;
}

.score-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  margin: 0.5rem 0;
  background-color: #f8f9fa;
  border-radius: 8px;
  transition: transform 0.2s;
}

.score-item:hover {
  transform: translateX(4px);
}

.score-item.winner {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  font-weight: bold;
  box-shadow: 0 4px 12px rgba(255, 215, 0, 0.3);
}

.score-item.current-player {
  border: 2px solid #3498db;
  background-color: #e3f2fd;
}

.rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background-color: #dee2e6;
  border-radius: 50%;
  font-weight: bold;
  font-size: 1.125rem;
}

.score-item.winner .rank {
  background-color: #fff;
  color: #ffd700;
}

.player-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.player-name {
  font-size: 1.125rem;
}

.player-badge {
  padding: 0.25rem 0.5rem;
  background-color: #e9ecef;
  border-radius: 3px;
  font-size: 0.75rem;
  color: #6c757d;
}

.score-item.winner .player-badge {
  background-color: rgba(255, 255, 255, 0.5);
  color: #000;
}

.player-score {
  font-size: 1.25rem;
  font-weight: bold;
  color: #2c3e50;
}

.score-item.winner .player-score {
  color: #000;
}

.button-group {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  justify-content: center;
  flex-wrap: wrap;
  align-items: center;
}

.ready-status {
  margin: 1.5rem 0;
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
}

.ready-indicator {
  padding: 0.75rem 1.5rem;
  background-color: #d4edda;
  color: #155724;
  border: 2px solid #c3e6cb;
  border-radius: 4px;
  font-weight: 500;
  font-size: 1rem;
  text-align: center;
  flex: 1;
  max-width: 400px;
}

.stats-card {
  margin-top: 2rem;
}

.stats-card h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  text-align: center;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1.5rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.stat-label {
  font-size: 0.875rem;
  color: #6c757d;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #2c3e50;
  text-transform: capitalize;
}

@media (max-width: 768px) {
  .winner-card h2 {
    font-size: 1.5rem;
  }

  .winner-score {
    font-size: 1.25rem;
  }

  .button-group {
    flex-direction: column;
  }

  .button-group button {
    width: 100%;
  }
}
</style>
