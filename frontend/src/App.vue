<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute } from "vue-router";

import SettingsPanel from "@/components/settings/SettingsPanel.vue";
import HdIconButton from "@/components/ui/HdIconButton.vue";
import HdToast from "@/components/ui/HdToast.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useSettingsPanel } from "@/composables/useSettingsPanel";
import { setLocale } from "@/i18n";
import { useAuthStore } from "@/stores/auth";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const authStore = useAuthStore();
const { connect, isConnected } = useGameConnection();
const route = useRoute();
const { t } = useI18n();
const { isOpen: settingsOpen, open: openSettings } = useSettingsPanel();

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
    <HdIconButton class="app-settings-btn" :label="t('settings.title')" @click="openSettings()">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="3" />
        <path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"
        />
      </svg>
    </HdIconButton>

    <RouterView />
    <HdToast />
    <SettingsPanel v-model:open="settingsOpen" />
  </div>
</template>

<style scoped>
#app {
  width: 100%;
  min-height: 100vh;
}
.app-settings-btn {
  position: fixed;
  /* Match the page gutter (~20px) so the gear sits in line with other UI
     rather than crowding the viewport edges. */
  top: max(20px, env(safe-area-inset-top));
  right: max(20px, env(safe-area-inset-right));
  z-index: 50;
}
</style>
