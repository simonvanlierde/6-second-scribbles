<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";

import GameHeader from "@/components/game/GameHeader.vue";
import DrawingRevealGrid from "@/components/results/DrawingRevealGrid.vue";
import RoundHighlights from "@/components/results/RoundHighlights.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdPill from "@/components/ui/HdPill.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const router = useRouter();
const { disconnect } = useGameConnection();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();

const countdown = ref(GAME_TIMINGS.ROUND_RESULTS_COUNTDOWN_S);
const leaveDialogOpen = ref(false);
let countdownInterval: number | null = null;

function avatarColorFor(playerId: string): string {
  return store.players.get(playerId)?.color ?? getAvatarColor(playerId);
}

const currentScores = computed(() =>
  store.playersList.map((p) => ({ id: p.id, name: p.name, score: p.score })).sort((a, b) => b.score - a.score),
);

const resultsByPlayer = computed(() => {
  const grouped: Record<
    string,
    { targetName: string; correctGuesses: number; totalItems: number; pointsEarned: number }[]
  > = {};

  for (const result of store.lastRoundResults) {
    const targetPlayer = store.players.get(result.targetPlayerId);
    const bucket = grouped[result.playerId] ?? [];
    bucket.push({
      targetName: targetPlayer?.name || i18n.global.t("common.unknown"),
      correctGuesses: result.correctGuesses,
      totalItems: result.totalItems,
      pointsEarned: result.pointsEarned,
    });
    grouped[result.playerId] = bucket;
  }

  return grouped;
});

const isLastRound = computed(() => store.currentRound >= store.maxRounds);

function leaveRoom() {
  disconnect();
  store.reset();
  router.push({ name: "home" });
}

function showLeaveDialog() {
  if (!shouldConfirm.value) {
    leaveRoom();
    return;
  }
  leaveDialogOpen.value = true;
}

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
  <div class="round-results">
    <GameHeader :time-left="countdown" @leave="showLeaveDialog" />

    <div class="round-results__body">
      <p class="round-results__lead">
        {{ $t("roundResults.title", { round: store.currentRound }) }}
        ·
        {{ isLastRound ? $t("roundResults.finalResultsSoon") : $t("roundResults.nextRoundSoon") }}
        {{ $t("common.countdownIn", { count: countdown }) }}
      </p>

      <RoundHighlights :highlights="store.lastHighlights" />

      <div class="round-results__columns">
        <section class="round-results__col">
          <h2 class="round-results__heading">{{ $t("roundResults.roundPerformance") }}</h2>
          <div class="performance">
            <HdCard v-for="player in store.playersList" :key="player.id" class="performance__card">
              <div class="performance__head">
                <HdAvatar :initial="getAvatarInitial(player.name)" :color="avatarColorFor(player.id)" size="sm" />
                <span class="performance__name">{{ player.name }}</span>
              </div>
              <ul v-if="resultsByPlayer[player.id]" class="performance__list">
                <li v-for="(result, index) in resultsByPlayer[player.id]" :key="index" class="performance__row">
                  <span class="performance__target">
                    {{ $t("roundResults.guessedPlayersDrawing", { name: result.targetName }) }}
                  </span>
                  <span class="performance__score">{{ result.correctGuesses }}/{{ result.totalItems }}</span>
                  <HdPill variant="success">+{{ $t("common.pointsShort", { count: result.pointsEarned }) }}</HdPill>
                </li>
              </ul>
              <p v-else class="performance__empty">{{ $t("roundResults.noGuessesSubmitted") }}</p>
            </HdCard>
          </div>
        </section>

        <section class="round-results__col">
          <h2 class="round-results__heading">{{ $t("roundResults.currentStandings") }}</h2>
          <HdCard class="standings">
            <div
              v-for="(player, index) in currentScores"
              :key="player.id"
              class="standings__row"
              :class="{ 'standings__row--you': player.id === store.localPlayerId }"
            >
              <span class="standings__rank">{{ index + 1 }}</span>
              <HdAvatar :initial="getAvatarInitial(player.name)" :color="avatarColorFor(player.id)" size="sm" />
              <span class="standings__name">{{ player.name }}</span>
              <HdPill v-if="player.id === store.localPlayerId" class="standings__you">{{ $t("common.you") }}</HdPill>
              <span class="standings__score">{{ $t("common.pointsShort", { count: player.score }) }}</span>
            </div>
          </HdCard>
        </section>
      </div>

      <DrawingRevealGrid />
    </div>

    <HdDialog
      v-model:open="leaveDialogOpen"
      :title="leaveDialog.title"
      :message="leaveDialog.message"
      :confirm-label="leaveDialog.confirmLabel"
      :cancel-label="leaveDialog.cancelLabel"
      variant="danger"
      @confirm="leaveRoom"
    />
  </div>
</template>

<style scoped>
.round-results {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-paper);
}
.round-results__body {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.round-results__lead {
  margin: 0;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink-muted);
}
.round-results__columns {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-6);
  align-items: start;
}
.round-results__heading {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
.performance {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.performance__head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.performance__name {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
  color: var(--color-ink);
}
.performance__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.performance__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.performance__target {
  flex: 1;
  min-width: 0;
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  color: var(--color-ink-muted);
}
.performance__score {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
}
.performance__empty {
  margin: 0;
  font-family: var(--font-body);
  font-style: italic;
  color: var(--color-ink-muted);
}
.standings {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.standings__row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--r-pill);
}
.standings__row--you {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.standings__rank {
  min-width: 1.25rem;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-marker-red);
}
.standings__name {
  flex: 1;
  min-width: 0;
  font-family: var(--font-body);
  font-weight: 700;
}
.standings__you {
  font-size: var(--text-label-sm);
}
.standings__score {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
}
@media (max-width: 768px) {
  .round-results__body {
    padding: var(--space-4);
    gap: var(--space-6);
  }
  .round-results__columns {
    grid-template-columns: 1fr;
  }
}
</style>
