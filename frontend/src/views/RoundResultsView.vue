<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { leaveRoom } = useLeaveRoom();

const countdown = ref(GAME_TIMINGS.ROUND_RESULTS_COUNTDOWN_S);
let countdownInterval: number | null = null;

const currentScores = computed(() =>
  store.playersList
    .map((p) => ({
      id: p.id,
      name: p.name,
      score: p.score,
    }))
    .sort((a, b) => b.score - a.score),
);

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
  countdownInterval = window.setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      clearInterval(countdownInterval ?? undefined);
      countdownInterval = null;
    }
  }, 1000);
});

onUnmounted(() => {
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }
});
</script>

<template>
  <div class="results-screen">
    <!-- Header -->
    <header class="results-header">
      <h1 class="round-title">Round {{ store.currentRound }} Results</h1>

      <div class="header-right">
        <div class="countdown-pill">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
          </svg>
          {{ isLastRound ? "Final results" : "Next round" }} in {{ countdown }}s
        </div>

        <button type="button" class="btn-leave" @click="leaveRoom">
          <svg
            width="14"
            height="14"
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
    </header>

    <div class="container">
      <!-- Round performance -->
      <section class="section">
        <h2 class="section-title">Round Performance</h2>
        <div class="results-grid">
          <div v-for="player in store.playersList" :key="player.id" class="player-card">
            <h3 class="player-card-name">{{ player.name }}</h3>

            <div v-if="resultsByPlayer[player.id]" class="guess-list">
              <div v-for="(result, index) in resultsByPlayer[player.id]" :key="index" class="guess-row">
                <span class="guess-target">Guessed {{ result.targetName }}'s drawing</span>
                <div class="guess-score">
                  <span class="correct-count">{{ result.correctGuesses }}/{{ result.totalItems }}</span>
                  <span class="points-earned">+{{ result.pointsEarned }} pts</span>
                </div>
              </div>
            </div>
            <p v-else class="no-guesses">No guesses submitted</p>
          </div>
        </div>
      </section>

      <!-- Standings -->
      <section class="section">
        <h2 class="section-title">Current Standings</h2>
        <div class="scoreboard card">
          <div
            v-for="(player, index) in currentScores"
            :key="player.id"
            class="score-row"
            :class="{ 'score-row--first': index === 0, 'score-row--me': player.id === store.localPlayerId }"
          >
            <span class="rank">{{ index + 1 }}</span>
            <span class="player-name">{{ player.name }}</span>
            <span v-if="player.id === store.localPlayerId" class="you-badge">You</span>
            <span class="score">{{ player.score }} pts</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.results-screen {
  min-height: 100vh;
  background: var(--color-bg-gradient);
  display: flex;
  flex-direction: column;
}

/* ── Header ────────────────────────────────────────────── */
.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1.5rem;
  background: rgba(0, 0, 0, 0.25);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  gap: 1rem;
  flex-wrap: wrap;
}

.round-title {
  margin: 0;
  font-size: 1.375rem;
  font-weight: 800;
  color: white;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.countdown-pill {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.4rem 0.875rem;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 999px;
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
}

.btn-leave {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.5rem 0.875rem;
  background: rgba(255, 255, 255, 0.12);
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  color: white;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-leave:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.75);
}

/* ── Container ─────────────────────────────────────────── */
.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* ── Sections ──────────────────────────────────────────── */
.section-title {
  margin: 0 0 0.875rem;
  font-size: 1.125rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── Player performance grid ───────────────────────────── */
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.player-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: 1.25rem;
  box-shadow: var(--shadow-md);
}

.player-card-name {
  margin: 0 0 0.875rem;
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--color-text-dark);
  border-bottom: 2px solid var(--color-primary);
  padding-bottom: 0.5rem;
}

.guess-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.guess-row {
  padding: 0.5rem 0.75rem;
  background: var(--color-surface);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-primary);
}

.guess-target {
  display: block;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-bottom: 0.25rem;
}

.guess-score {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.correct-count {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-dark);
}

.points-earned {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-primary);
}

.no-guesses {
  color: var(--color-text-muted);
  font-style: italic;
  font-size: 0.875rem;
  margin: 0;
  padding: 0.5rem 0;
}

/* ── Scoreboard ────────────────────────────────────────── */
.scoreboard {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  padding: 1.25rem;
}

.score-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  font-size: 1rem;
  transition: transform 0.15s;
}

.score-row--first {
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
  font-weight: 700;
}

.score-row--me {
  border: 2px solid var(--color-primary);
  background: #ebf0ff;
}

.score-row--first.score-row--me {
  border-color: #b8860b;
  background: linear-gradient(135deg, #ffd700 0%, #ffed4e 100%);
}

.rank {
  font-weight: 800;
  color: var(--color-primary);
  min-width: 1.5rem;
  font-size: 1.0625rem;
}

.score-row--first .rank {
  color: #b8860b;
}

.player-name {
  flex: 1;
  font-weight: 500;
}

.you-badge {
  padding: 0.15rem 0.5rem;
  background: var(--color-primary);
  color: white;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.score-row--first .you-badge {
  background: #b8860b;
}

.score {
  font-weight: 700;
  color: var(--color-primary);
}

.score-row--first .score {
  color: #b8860b;
}

/* ── Mobile ────────────────────────────────────────────── */
@media (max-width: 768px) {
  .results-header {
    padding: 0.75rem 1rem;
  }

  .round-title {
    font-size: 1.125rem;
  }

  .container {
    padding: 1rem;
  }

  .results-grid {
    grid-template-columns: 1fr;
  }
}
</style>
