<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";

import { useGameConnection } from "@/composables/useGameConnection";
import { normalizeGamePhase } from "@/shared/gamePhase";
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
const gamePhase = computed(() => normalizeGamePhase(store.gamePhase));
const isSpectating = computed(
  () =>
    (!inActiveRoom.value && store.isSpectatorMode && gamePhase.value !== "lobby") ||
    (!inActiveRoom.value && (gamePhase.value === "drawing" || gamePhase.value === "guessing")),
);
// While we intend to be in this room but the server's authoritative snapshot has
// not yet been applied (initial load / reconnect after a reload), render a
// connecting state rather than a screen built from non-authoritative state.
const isConnecting = computed(() => inActiveRoom.value && !store.hydrated);
</script>

<template>
  <RoomAccessView v-if="!inActiveRoom && !isSpectating" />
  <SpectatorRoomView v-else-if="isSpectating" />
  <div v-else-if="isConnecting" class="room-connecting">
    <div class="room-connecting__card">
      <span class="room-connecting__spinner" aria-hidden="true" />
      <p>{{ $t("common.connecting") }}</p>
    </div>
  </div>
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
</style>
