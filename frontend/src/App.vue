<script setup lang="ts">
import { onMounted, watch } from "vue";
import { useI18n } from "vue-i18n";

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
const { connectionStatus } = useGameConnection();
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
  // The websocket (re)connect is owned by RoomView, which only mounts once the
  // room route is resolved — avoiding the route-not-ready race this used to hit.
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
    <!-- Non-blocking reconnect banner: shown when an established session drops and
         is auto-recovering, so the game view stays mounted (canvas/state intact). -->
    <Transition name="reconnect-banner">
      <div v-if="connectionStatus === 'reconnecting' && store.hydrated" class="reconnect-banner" role="status">
        <span class="reconnect-banner__spinner" aria-hidden="true" />
        {{ t("common.reconnecting") }}
      </div>
    </Transition>
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
.reconnect-banner {
  position: fixed;
  top: max(16px, env(safe-area-inset-top));
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 16px;
  border-radius: var(--r-pill);
  background: var(--color-ink);
  color: var(--color-paper);
  font-family: var(--font-display);
  font-size: var(--text-label-md);
  box-shadow: var(--shadow-md, 0 4px 12px rgb(0 0 0 / 25%));
}
.reconnect-banner__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid color-mix(in srgb, var(--color-paper) 35%, transparent);
  border-top-color: var(--color-paper);
  border-radius: var(--r-pill);
  animation: reconnect-spin 0.8s linear infinite;
}
@keyframes reconnect-spin {
  to {
    transform: rotate(360deg);
  }
}
.reconnect-banner-enter-active,
.reconnect-banner-leave-active {
  transition: opacity 0.2s ease;
}
.reconnect-banner-enter-from,
.reconnect-banner-leave-to {
  opacity: 0;
}
</style>
