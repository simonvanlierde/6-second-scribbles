<script setup lang="ts">
import { onMounted } from "vue";

import ToastContainer from "@/components/ToastContainer.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { connect, isConnected } = useGameConnection();

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
