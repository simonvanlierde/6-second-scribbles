<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";

import ToastContainer from "@/components/ToastContainer.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { setLocale } from "@/i18n";
import { useAuthStore } from "@/stores/auth";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const authStore = useAuthStore();
const { connect, isConnected } = useGameConnection();
const route = useRoute();

watch(
  () => store.localPlayerLocale,
  (newLocale) => {
    if (newLocale) {
      void setLocale(newLocale);
    }
  },
  { immediate: true },
);

onMounted(async () => {
  await authStore.bootstrap(store.localPlayerLocale, store.localPlayerName || null);
  if (authStore.currentUser?.preferredLocale) {
    store.setLocalPlayerLocale(authStore.currentUser.preferredLocale);
  }
  if (authStore.currentUser?.displayName && !store.localPlayerName) {
    store.localPlayerName = authStore.currentUser.displayName;
  }

  const routeRoomCode = typeof route.params.roomCode === "string" ? route.params.roomCode : "";
  if (store.roomCode && store.localPlayerId && !isConnected.value && routeRoomCode === store.roomCode) {
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
