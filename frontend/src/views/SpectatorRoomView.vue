<script setup lang="ts">
import { computed } from "vue";

import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdPill from "@/components/ui/HdPill.vue";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { leaveRoom } = useLeaveRoom();

const drawings = computed(() => store.playersList.filter((player) => player.drawing));
// RoomView only renders this view outside the lobby, so no lobby label is needed.
const phaseLabel = computed(() => {
  if (store.gamePhase === "drawing") return i18n.global.t("spectator.drawingRound");
  if (store.gamePhase === "guessing") return i18n.global.t("spectator.guessingRound");
  if (store.gamePhase === "round_results") return i18n.global.t("spectator.roundResults");
  if (store.gamePhase === "final_results") return i18n.global.t("spectator.finalResults");
  return i18n.global.t("spectator.watchingRoom");
});
</script>

<template>
  <div class="spectator-page">
    <header class="spectator-topbar">
      <div class="spectator-topbar__info">
        <span class="spectator-code">
          <span class="spectator-code__label">{{ $t('home.roomCodeLabel') }}</span>
          <span class="spectator-code__value">{{ store.roomCode }}</span>
        </span>
        <h1 class="spectator-title">{{ phaseLabel }}</h1>
        <p class="spectator-sub">{{ $t("spectator.watchingLive") }}</p>
      </div>
      <HdButton variant="secondary" class="leave-btn" @click="leaveRoom"> {{ $t("spectator.leaveRoom") }} </HdButton>
    </header>

    <HdCard class="spectator-section">
      <h2 class="spectator-section__title">{{ $t("spectator.players") }}</h2>
      <div class="spectator-players">
        <HdPill v-for="player in store.playersList" :key="player.id">
          {{ player.name }}
          <span class="spectator-players__score">{{ $t("common.pointsShort", { count: player.score }) }}</span>
        </HdPill>
      </div>
    </HdCard>

    <HdCard v-if="store.gamePhase === 'drawing'" class="spectator-section">
      <h2 class="spectator-section__title">{{ $t("spectator.drawings") }}</h2>
      <div v-if="drawings.length" class="spectator-drawings">
        <figure v-for="player in drawings" :key="player.id" class="spectator-drawing">
          <img
            :src="player.drawing"
            :alt="$t('spectator.drawingAlt', { name: player.name })"
            class="spectator-drawing__img"
          >
          <figcaption class="spectator-drawing__name">{{ player.name }}</figcaption>
        </figure>
      </div>
      <p v-else class="spectator-body">{{ $t("spectator.noDrawingsYet") }}</p>
    </HdCard>

    <HdCard v-else class="spectator-section">
      <h2 class="spectator-section__title">{{ $t("spectator.roundStatus") }}</h2>
      <p v-if="store.gamePhase === 'guessing'" class="spectator-body">{{ $t("spectator.guessingInProgress") }}</p>
      <p v-else class="spectator-body">{{ $t("spectator.betweenRounds") }}</p>
    </HdCard>
  </div>
</template>

<style scoped>
.spectator-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  position: relative;
  z-index: 1;
}
.spectator-topbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  /* Clear the globally-fixed settings gear (App.vue, top/right ≈ 20px). */
  padding-right: calc(var(--space-4) + 52px);
}
.spectator-code {
  display: inline-flex;
  align-items: baseline;
  gap: 10px;
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
  border: 2px dashed var(--color-ink);
  border-radius: 12px 18px 14px 22px;
  padding: 4px 14px;
}
.spectator-code__label {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  opacity: 0.7;
}
.spectator-code__value {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.3em;
}
.spectator-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-display-sm);
  line-height: 1.15;
  margin: 10px 0 0;
  color: var(--color-ink);
}
.spectator-sub {
  font-family: var(--font-body);
  color: var(--color-ink-muted);
  margin: 4px 0 0;
}
.spectator-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.spectator-section__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
  color: var(--color-ink);
}
.spectator-players {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.spectator-players__score {
  color: var(--color-ink-muted);
}
.spectator-drawings {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}
.spectator-drawing {
  margin: 0;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-input);
  overflow: hidden;
  background: var(--color-paper);
}
.spectator-drawing__img {
  display: block;
  width: 100%;
  height: 180px;
  object-fit: contain;
}
.spectator-drawing__name {
  padding: 8px 12px;
  font-family: var(--font-body);
  color: var(--color-ink);
  border-top: 1.5px dashed var(--color-ink);
}
.spectator-body {
  font-family: var(--font-body);
  color: var(--color-ink-muted);
  margin: 0;
}
</style>
