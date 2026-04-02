<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { injectGameEngine } from "@/composables/injectionKeys";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const gameEngineRef = injectGameEngine();
const { leaveRoom } = useLeaveRoom(gameEngineRef);

const countdown = ref(5);

const currentScores = computed(() =>
  store.playersList
    .map((p) => ({
      id: p.id,
      name: p.name,
      score: p.score,
    }))
    .sort((a, b) => b.score - a.score),
);

// Group results by player who made the guesses
const resultsByPlayer = computed(() => {
  const grouped: Record<
    string,
    { targetName: string; correctGuesses: number; totalItems: number; pointsEarned: number }[]
  > = {};

  for (const result of store.lastRoundResults) {
    if (!grouped[result.playerId]) {
      grouped[result.playerId] = [];
    }

    const targetPlayer = store.players.get(result.targetPlayerId);
    const arr = grouped[result.playerId] as {
      targetName: string;
      correctGuesses: number;
      totalItems: number;
      pointsEarned: number;
    }[];
    arr.push({
      targetName: targetPlayer?.name || "Unknown",
      correctGuesses: result.correctGuesses,
      totalItems: result.totalItems,
      pointsEarned: result.pointsEarned,
    });
  }

  return grouped;
});

const isLastRound = computed(() => store.currentRound >= store.maxRounds);

onMounted(() => {
  const interval = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(interval);
      // Host drives the next round after the countdown.
      if (store.isHost && !isLastRound.value) {
        gameEngineRef?.value?.startRound(store.currentRound + 1, store.difficulty, store.roundLength);
      }
    }
  }, 1000);
});
</script>

<template>
  <div class="results-screen">
    <div class="container">
      <div style="display: flex; justify-content: flex-end">
        <button type="button" class="btn btn-secondary btn-leave" @click="leaveRoom">🚪 Leave</button>
      </div>
      <h1>Round {{ store.currentRound }} Results</h1>

      <div class="countdown-banner">
        <span v-if="!isLastRound">Next round starts in {{ countdown }}s...</span>
        <span v-else>Final results in {{ countdown }}s...</span>
      </div>

      <div class="results-section">
        <h2>Round Performance</h2>
        <div class="results-grid">
          <div v-for="player in store.playersList" :key="player.id" class="player-results-card">
            <h3>{{ player.name }}</h3>

            <div v-if="resultsByPlayer[player.id]" class="player-guesses">
              <div v-for="(result, index) in resultsByPlayer[player.id]" :key="index" class="guess-result">
                <div class="guess-target">Guessing {{ result.targetName }}'s drawing:</div>
                <div class="guess-score">
                  <span class="correct">{{ result.correctGuesses }}</span>
                  /
                  {{ result.totalItems }}
                  correct
                  <span class="points">+{{ result.pointsEarned }} pts</span>
                </div>
              </div>
            </div>
            <div v-else class="no-guesses">No guesses submitted</div>
          </div>
        </div>
      </div>

      <div class="scores-section">
        <h2>Current Standings</h2>
        <div class="scoreboard">
          <div v-for="(player, index) in currentScores" :key="player.id" class="score-entry">
            <span class="rank">{{ index + 1 }}.</span>
            <span class="name">{{ player.name }}</span>
            <span class="score">{{ player.score }} pts</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.results-screen {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 2rem;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  color: white;
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.countdown-banner {
  text-align: center;
  background: rgba(255, 255, 255, 0.2);
  backdrop-filter: blur(10px);
  color: white;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  font-size: 1.25rem;
  font-weight: 500;
}

.results-section {
  margin-bottom: 2rem;
}

.results-section h2 {
  color: white;
  font-size: 1.75rem;
  margin-bottom: 1rem;
  text-align: center;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.player-results-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.player-results-card h3 {
  margin: 0 0 1rem 0;
  color: #2c3e50;
  font-size: 1.5rem;
  border-bottom: 2px solid #667eea;
  padding-bottom: 0.5rem;
}

.player-guesses {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.guess-result {
  padding: 0.75rem;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.guess-target {
  font-weight: 500;
  color: #495057;
  margin-bottom: 0.5rem;
}

.guess-score {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.guess-score .correct {
  color: #28a745;
  font-weight: bold;
  font-size: 1.25rem;
}

.guess-score .points {
  margin-left: auto;
  color: #667eea;
  font-weight: 600;
  font-size: 1rem;
}

.no-guesses {
  color: #6c757d;
  font-style: italic;
  text-align: center;
  padding: 1rem;
}

.scores-section {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.scores-section h2 {
  color: #2c3e50;
  margin-bottom: 1.5rem;
}

.scoreboard {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.score-entry {
  display: flex;
  align-items: center;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 1.125rem;
}

.score-entry:first-child {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  font-weight: 600;
  font-size: 1.25rem;
}

.score-entry .rank {
  font-weight: bold;
  color: #667eea;
  min-width: 2rem;
}

.score-entry:first-child .rank {
  color: #b8860b;
}

.score-entry .name {
  flex: 1;
  margin-left: 0.5rem;
}

.score-entry .score {
  font-weight: 600;
  color: #667eea;
}

.score-entry:first-child .score {
  color: #b8860b;
}

@media (max-width: 768px) {
  h1 {
    font-size: 2rem;
  }

  .results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
