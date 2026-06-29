<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

import GameHeader from "@/components/game/GameHeader.vue";
import AllDrawingsGallery from "@/components/results/AllDrawingsGallery.vue";
import WinnerCard from "@/components/results/WinnerCard.vue";
import HdAvatar from "@/components/ui/HdAvatar.vue";
import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdDialog from "@/components/ui/HdDialog.vue";
import HdPill from "@/components/ui/HdPill.vue";
import { getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { useRoomLeave } from "@/composables/useRoomLeave";
import { useSound } from "@/composables/useSound";
import { GAME_TIMINGS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();
const { shouldConfirm, dialog: leaveDialog } = useRoomLeave();
const { play } = useSound();
const { leaveRoom } = useLeaveRoom(() => clearAutoRestartTimeout());

const isReady = ref(false);
const autoRestartTimeout = ref<number | null>(null);
const leaveDialogOpen = ref(false);

const finalScores = computed(() => store.getFinalScores());

const rankedScores = computed(() => {
  const scores = finalScores.value;
  const ranked: Array<(typeof scores)[number] & { rank: number; isTied: boolean }> = [];

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
const winnerIsTie = computed(() => winners.value.length > 1);
const winnerNames = computed(() => formatNames(winners.value.map((player) => player.playerName)));
const winnerScore = computed(() => winners.value[0]?.score ?? 0);
const winnerInitial = computed(() => getAvatarInitial(winners.value[0]?.playerName ?? "?"));
const winnerColor = computed(() => avatarColorFor(winners.value[0]?.playerId ?? ""));

function avatarColorFor(playerId: string): string {
  return store.players.get(playerId)?.color ?? getAvatarColor(playerId);
}

function formatNames(names: string[]) {
  if (names.length <= 1) return names[0] || i18n.global.t("common.unknown");
  if (names.length === 2) return `${names[0]} ${i18n.global.t("common.and")} ${names[1]}`;
  return names.join(", ");
}

watch(
  () => store.gamePhase,
  (newPhase) => {
    if (newPhase === "lobby") clearAutoRestartTimeout();
  },
);

watch(
  () => store.readyCount,
  (newReadyCount) => {
    if (!store.isHost) return;
    if (newReadyCount > 0 && newReadyCount === store.totalPlayers) {
      clearAutoRestartTimeout();
      autoRestartTimeout.value = window.setTimeout(() => {
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
    send({ type: "restart_game" });
    store.resetRound();
    store.gamePhase = "lobby";
  } else {
    isReady.value = true;
    send({ type: "player_ready", playerId: store.localPlayerId });
  }
}

function showLeaveDialog() {
  if (!shouldConfirm.value) {
    leaveRoom();
    return;
  }
  leaveDialogOpen.value = true;
}

onMounted(() => {
  play("winner");
});

onUnmounted(() => {
  clearAutoRestartTimeout();
});
</script>

<template>
  <div class="final-results">
    <GameHeader
      variant="final"
      :title="$t('finalResults.gameOver')"
      :status="$t('finalResults.playersReady', { count: store.readyCount, total: store.totalPlayers })"
      @leave="showLeaveDialog"
    />

    <div class="final-results__body">
      <WinnerCard
        :name="winnerNames"
        :initial="winnerInitial"
        :color="winnerColor"
        :score="winnerScore"
        :is-tie="winnerIsTie"
      />

      <div class="final-results__columns">
        <section class="final-results__col">
          <h2 class="final-results__heading">{{ $t("finalResults.standings") }}</h2>
          <HdCard class="final-standings">
            <div
              v-for="player in rankedScores"
              :key="player.playerId"
              class="final-standings__row"
              :class="{ 'final-standings__row--you': player.playerId === store.localPlayerId }"
            >
              <span class="final-standings__rank">{{ player.rank }}</span>
              <HdAvatar
                :initial="getAvatarInitial(player.playerName)"
                :color="avatarColorFor(player.playerId)"
                size="sm"
              />
              <span class="final-standings__name">{{ player.playerName }}</span>
              <HdPill v-if="player.playerId === store.localPlayerId" class="final-standings__tag">
                {{ $t("common.you") }}
              </HdPill>
              <span class="final-standings__score">{{ $t("common.pointsShort", { count: player.score }) }}</span>
            </div>
          </HdCard>

          <HdCard variant="postit" class="final-stats">
            <h3 class="final-stats__title">{{ $t("finalResults.gameStats") }}</h3>
            <dl class="final-stats__grid">
              <div class="final-stats__item">
                <dt>{{ $t("finalResults.statRounds") }}</dt>
                <dd>{{ store.maxRounds }}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{{ $t("finalResults.statPlayers") }}</dt>
                <dd>{{ store.playersList.length }}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{{ $t("finalResults.statDifficulty") }}</dt>
                <dd class="final-stats__difficulty">{{ store.difficulty }}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{{ $t("finalResults.statDrawings") }}</dt>
                <dd>{{ store.drawingHistory.length }}</dd>
              </div>
              <div class="final-stats__item">
                <dt>{{ $t("finalResults.statGuesses") }}</dt>
                <dd>{{ store.totalGuessesMade }}</dd>
              </div>
            </dl>
          </HdCard>
        </section>

        <section class="final-results__col"><AllDrawingsGallery :drawings="store.drawingHistory" /></section>
      </div>

      <div class="final-cta">
        <HdButton class="final-cta__again" variant="primary" @click="playAgain">
          {{ store.isHost ? $t("finalResults.playAgain") : isReady ? $t("finalResults.readyWaiting") : $t("finalResults.readyForNext") }}
        </HdButton>
        <HdButton class="final-cta__home" variant="success" @click="showLeaveDialog">
          {{ $t("finalResults.backHome") }}
        </HdButton>
      </div>
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
.final-results {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--color-paper);
}
.final-results__body {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}
.final-results__columns {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: var(--space-6);
  align-items: start;
}
.final-results__col {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  min-width: 0;
}
.final-results__heading {
  margin: 0 0 var(--space-3);
  font-size: var(--text-heading-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-ink);
}
.final-standings {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.final-standings__row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--r-pill);
}
.final-standings__row--you {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.final-standings__rank {
  min-width: 1.25rem;
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-marker-red);
}
.final-standings__name {
  flex: 1;
  min-width: 0;
  font-family: var(--font-body);
  font-weight: 700;
}
.final-standings__tag {
  font-size: var(--text-label-sm);
}
.final-standings__score {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink);
}
.final-stats__title {
  margin: 0 0 var(--space-3);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
}
.final-stats__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(90px, 1fr));
  gap: var(--space-3);
  margin: 0;
}
.final-stats__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.final-stats__item dt {
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  opacity: 0.75;
}
.final-stats__item dd {
  margin: 0;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-sm);
}
.final-stats__difficulty {
  text-transform: capitalize;
}
.final-cta {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-4);
}
@media (max-width: 768px) {
  .final-results__body {
    padding: var(--space-4);
    gap: var(--space-6);
  }
  .final-results__columns {
    grid-template-columns: 1fr;
  }
  .final-cta {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
