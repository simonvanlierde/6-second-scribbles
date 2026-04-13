<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";

import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const { leaveRoom: _leaveRoom } = useLeaveRoom();
const isReady = ref(false);
const autoRestartTimeout = ref<number | null>(null);

const finalScores = computed(() => store.getFinalScores());

const rankedScores = computed(() => {
  const scores = finalScores.value;
  const ranked: Array<
    (typeof scores)[number] & {
      rank: number;
      isTied: boolean;
    }
  > = [];

  let index = 0;
  while (index < scores.length) {
    const score = scores[index]?.score ?? 0;
    let groupEnd = index + 1;

    while (groupEnd < scores.length && scores[groupEnd]?.score === score) {
      groupEnd += 1;
    }

    const rank = index + 1;
    const isTied = groupEnd - index > 1;

    for (let i = index; i < groupEnd; i += 1) {
      const player = scores[i];
      if (!player) continue;
      ranked.push({ ...player, rank, isTied });
    }

    index = groupEnd;
  }

  return ranked;
});

const winners = computed(() => rankedScores.value.filter((player) => player.rank === 1));
const winnerHeading = computed(() => (winners.value.length > 1 ? "Winners" : "Winner"));
const winnerNames = computed(() => formatNames(winners.value.map((player) => player.playerName)));
const winnerScoreText = computed(() =>
  winners.value.length > 1
    ? `Tied at ${winners.value[0]?.score ?? 0} points`
    : `${winners.value[0]?.score ?? 0} points`,
);

function formatNames(names: string[]) {
  if (names.length <= 1) return names[0] || "Unknown";
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return names.join(", ");
}

function formatOrdinal(rank: number) {
  const remainder100 = rank % 100;
  if (remainder100 >= 11 && remainder100 <= 13) return `${rank}th`;

  const remainder10 = rank % 10;
  if (remainder10 === 1) return `${rank}st`;
  if (remainder10 === 2) return `${rank}nd`;
  if (remainder10 === 3) return `${rank}rd`;
  return `${rank}th`;
}

// Watch for game phase changes (when host starts new game)
watch(
  () => store.gamePhase,
  (newPhase) => {
    if (newPhase === "lobby") {
      // Host started a new game, redirect to waiting room
      clearAutoRestartTimeout();
    }
  },
);

// Watch for all players ready - host initiates auto-restart after 60s
watch(
  () => store.readyCount,
  (newReadyCount) => {
    // Only host handles auto-restart
    if (!store.isHost) return;

    // Check if all players are ready
    if (newReadyCount > 0 && newReadyCount === store.totalPlayers) {
      console.log("[ResultsView] All players ready. Auto-restart in 60 seconds.");

      // Set timeout for auto-restart
      clearAutoRestartTimeout();
      autoRestartTimeout.value = window.setTimeout(() => {
        console.log("[ResultsView] Auto-restart timeout reached. Restarting game.");
        playAgain();
      }, GAME_TIMINGS.AUTO_RESTART_TIMEOUT_MS);
    }
  },
);

function clearAutoRestartTimeout() {
  if (autoRestartTimeout.value) {
    clearTimeout(autoRestartTimeout.value);
    autoRestartTimeout.value = null;
  }
}

function playAgain() {
  if (store.isHost) {
    // Host broadcasts restart_game message to all players
    send({
      type: "restart_game",
    });

    // Reset scores and round counter via store action
    store.resetRound();

    // Reset game state to lobby
    store.gamePhase = "lobby";

  } else {
    // Non-host indicates they're ready to play again
    isReady.value = true;
    send({
      type: "player_ready",
      playerId: store.localPlayerId,
    });
  }
}

function leaveRoom() {
  clearAutoRestartTimeout();
  _leaveRoom();
}

onUnmounted(() => {
  clearAutoRestartTimeout();
});
</script>

<template>
  <div class="screen">
    <div class="container">
      <h1>{{ $t('results.gameOver') }}</h1>

      <div class="card winner-card">
        <div class="trophy-icon">🎉</div>
        <h2>{{ winnerHeading }}: {{ winnerNames }}</h2>
        <p class="winner-score">{{ winnerScoreText }}</p>
      </div>

      <div class="card">
        <h2>{{ $t('results.finalScores') }}</h2>
        <div class="scores-list">
          <div
            v-for="player in rankedScores"
            :key="player.playerId"
            class="score-item"
            :class="{
              winner: player.rank === 1,
              tied: player.isTied,
              'current-player': player.playerId === store.localPlayerId,
            }"
          >
            <div class="rank">{{ player.rank }}</div>
            <div class="player-info">
              <span class="player-name">{{ player.playerName }}</span>
              <span v-if="player.playerId === store.localPlayerId" class="player-badge">{{ $t('results.you') }}</span>
              <span v-if="player.isTied" class="player-badge tie-badge">{{ $t('results.tiedForRank', { rank: formatOrdinal(player.rank) }) }}</span>
            </div>
            <div class="player-score">{{ $t('results.pts', { score: player.score }) }}</div>
          </div>
        </div>

        <!-- Ready status display for all players -->
        <div class="ready-status">
          <p class="ready-count">{{ $t('results.playersReady', { count: store.readyCount, total: store.totalPlayers }) }}</p>
        </div>

        <div class="button-group">
          <button v-if="store.isHost" type="button" class="btn btn-primary" @click="playAgain">{{ $t('results.playAgain') }}</button>
          <button v-else-if="!isReady" type="button" class="btn btn-primary" @click="playAgain">
            {{ $t('results.readyForNext') }}
          </button>
          <div v-else class="ready-indicator">{{ $t('results.readyWaiting') }}</div>
          <button type="button" class="btn btn-secondary" @click="leaveRoom">{{ $t('results.leaveRoom') }}</button>
        </div>
      </div>

      <div class="card stats-card">
        <h3>{{ $t('results.gameStatistics') }}</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">{{ $t('results.totalRounds') }}</div>
            <div class="stat-value">{{ store.maxRounds }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">{{ $t('results.players') }}</div>
            <div class="stat-value">{{ store.playersList.length }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">{{ $t('results.difficulty') }}</div>
            <div class="stat-value">{{ store.difficulty }}</div>
          </div>
        </div>
      </div>
    </div>
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

.score-item.tied .rank {
  background-color: #f0ad4e;
  color: white;
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

.tie-badge {
  background-color: rgba(52, 152, 219, 0.15);
  color: #1f6fb2;
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
