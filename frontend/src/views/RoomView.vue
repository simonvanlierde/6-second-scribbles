<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

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
const routeRoomCode = computed(() => normalizeRoomCode(String(route.params.roomCode || "")));
const inActiveRoom = computed(() => Boolean(store.localPlayerId) && store.roomCode === routeRoomCode.value);
const gamePhase = computed(() => normalizeGamePhase(store.gamePhase));
const isSpectating = computed(
  () =>
    (!inActiveRoom.value && store.isSpectatorMode && gamePhase.value !== "lobby") ||
    (!inActiveRoom.value && (gamePhase.value === "drawing" || gamePhase.value === "guessing")),
);
</script>

<template>
  <RoomAccessView v-if="!inActiveRoom && !isSpectating" />
  <SpectatorRoomView v-else-if="isSpectating" />
  <LobbyView v-else-if="gamePhase === 'lobby'" />
  <GameView v-else-if="gamePhase === 'drawing' || gamePhase === 'guessing'" />
  <RoundResultsView v-else-if="gamePhase === 'round_results'" />
  <ResultsView v-else-if="gamePhase === 'final_results'" />
  <LobbyView v-else />
</template>
