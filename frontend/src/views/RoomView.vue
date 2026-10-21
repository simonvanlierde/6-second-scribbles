<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, watch, watchEffect } from "vue";
import { useRoute } from "vue-router";

import { useAnnouncer } from "@/composables/useAnnouncer";
import { useGameConnection } from "@/composables/useGameConnection";
import { i18n } from "@/i18n";
import { normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game";
import GameView from "@/views/GameView.vue";
import LobbyView from "@/views/LobbyView.vue";
import ResultsView from "@/views/ResultsView.vue";
import RoomAccessView from "@/views/RoomAccessView.vue";
import RoundResultsView from "@/views/RoundResultsView.vue";
import SpectatorRoomView from "@/views/SpectatorRoomView.vue";

const store = useGameStore();
const route = useRoute();
const { connect, connectionStatus } = useGameConnection();
const routeRoomCode = computed(() => normalizeRoomCode(String(route.params.roomCode || "")));
const inActiveRoom = computed(() => Boolean(store.localPlayerId) && store.roomCode === routeRoomCode.value);

// Owning the (re)connect here — rather than in App.vue's one-shot onMounted —
// is reliable: this view only renders once the room route is resolved, so the
// normalized room code and persisted identity are available. Covers reload /
// returning to a room; the connection layer auto-reconnects on later drops.
function ensureConnected() {
  if (inActiveRoom.value && connectionStatus.value === "disconnected") {
    connect(routeRoomCode.value);
  }
}
onMounted(ensureConnected);
watch(inActiveRoom, ensureConnected);
const gamePhase = computed(() => store.gamePhase);
const isSpectating = computed(
  () =>
    (!inActiveRoom.value && store.isSpectatorMode && gamePhase.value !== "lobby") ||
    (!inActiveRoom.value && (gamePhase.value === "drawing" || gamePhase.value === "guessing")),
);
// While we intend to be in this room but the server's authoritative snapshot has
// not yet been applied (initial load / reconnect after a reload), render a
// connecting state rather than a screen built from non-authoritative state.
const isConnecting = computed(() => inActiveRoom.value && !store.hydrated);

const { t } = i18n.global;
const { announce } = useAnnouncer();
const defaultTitle = document.title;

const pageTitle = computed(() => {
  if (isSpectating.value) return t("spectator.watchingRoom");
  if (!inActiveRoom.value) return t("roomAccess.joinRoom");
  if (isConnecting.value) return t("common.connecting");
  const round = store.currentRound;
  switch (gamePhase.value) {
    case "drawing":
      return t("phase.drawing", { round });
    case "guessing":
      return t("phase.guessing", { round });
    case "round_results":
      return t("roundResults.title", { round });
    case "final_results":
      return t("finalResults.gameOver");
    default:
      return t("roomAccess.lobby");
  }
});
watchEffect(() => {
  document.title = `${pageTitle.value} · ${t("home.title")}`;
});
onUnmounted(() => {
  document.title = defaultTitle;
});

// A phase change swaps the whole screen, which would drop keyboard focus to <body>
// and say nothing to a screen reader: announce the new phase and focus its heading.
watch(gamePhase, async () => {
  if (!store.hydrated) return;
  announce(pageTitle.value);
  if (!inActiveRoom.value) return;
  await nextTick();
  const heading = document.querySelector<HTMLElement>("main h1");
  if (!heading) return;
  heading.setAttribute("tabindex", "-1");
  heading.focus();
});
</script>

<template>
  <RoomAccessView v-if="!inActiveRoom && !isSpectating" />
  <SpectatorRoomView v-else-if="isSpectating" />
  <main v-else-if="isConnecting" class="room-connecting">
    <div class="room-connecting__card">
      <span class="room-connecting__spinner" aria-hidden="true" />
      <h1 class="room-connecting__text">{{ $t("common.connecting") }}</h1>
    </div>
  </main>
  <LobbyView v-else-if="gamePhase === 'lobby'" />
  <GameView v-else-if="gamePhase === 'drawing' || gamePhase === 'guessing'" />
  <RoundResultsView v-else-if="gamePhase === 'round_results'" />
  <ResultsView v-else-if="gamePhase === 'final_results'" />
  <LobbyView v-else />
</template>

<style scoped>
.room-connecting {
  display: flex;
  min-height: 100dvh;
  align-items: center;
  justify-content: center;
  background: var(--color-paper);
}
.room-connecting__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-display);
  font-size: var(--text-heading-sm);
  color: var(--color-ink);
}
.room-connecting__text {
  margin: 0;
  font-size: inherit;
}
.room-connecting__spinner {
  width: 36px;
  height: 36px;
  border: 3px solid color-mix(in srgb, var(--color-ink) 20%, transparent);
  border-top-color: var(--color-ink);
  border-radius: var(--r-pill);
  animation: room-connecting-spin 0.8s linear infinite;
}
@keyframes room-connecting-spin {
  to {
    transform: rotate(360deg);
  }
}
/* No spinning for reduced motion: a slow fade still shows it is working. */
@media (prefers-reduced-motion: reduce) {
  .room-connecting__spinner {
    animation: room-connecting-pulse 2s ease-in-out infinite;
  }
}
@keyframes room-connecting-pulse {
  50% {
    opacity: 0.4;
  }
}
</style>
