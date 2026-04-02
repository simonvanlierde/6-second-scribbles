<script setup lang="ts">
import { onMounted, provide, shallowRef, watch } from "vue";

import ToastContainer from "@/components/ToastContainer.vue";
import { gameEngineKey } from "@/composables/injectionKeys";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameEngine } from "@/composables/useGameEngine";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { connect, isConnected } = useGameConnection();

// Single engine ref for the entire app. WaitingRoomView sets this when the
// host starts a game; views clear it on leave/restart. Non-host players
// leave it null — the engine only runs on the host's client.
const gameEngine = shallowRef<ReturnType<typeof useGameEngine> | null>(null);
provide(gameEngineKey, gameEngine);

// If this player becomes the host mid-game (e.g. original host disconnected),
// reconstruct the engine so they can drive round progression.
watch(
  () => store.isHost,
  (isHost) => {
    if (isHost && !gameEngine.value && store.gamePhase !== "lobby" && store.gamePhase !== "complete") {
      gameEngine.value = useGameEngine();
    }
  },
);

// Reconnect to room on page reload if we have saved state
onMounted(() => {
  if (store.roomCode && store.localPlayerId && !isConnected.value) {
    console.log("Reconnecting to room:", store.roomCode);
    connect(store.roomCode);
  }
});
</script>

<template>
  <div id="app">
    <RouterView />
    <ToastContainer />
  </div>
</template>

<style scoped>
#app {
  width: 100%;
  min-height: 100vh;
}
</style>
