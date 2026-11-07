<script lang="ts">
import { setLinguiContext } from "lingui-for-svelte";
import { t as translate } from "lingui-for-svelte/macro";
import { onMount } from "svelte";
import { fade } from "svelte/transition";
import SettingsPanel from "@/components/settings/SettingsPanel.svelte";
import HdIconButton from "@/components/ui/HdIconButton.svelte";
import HdToast from "@/components/ui/HdToast.svelte";
import { useAnnouncer } from "@/composables/useAnnouncer.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { useSettingsPanel } from "@/composables/useSettingsPanel.svelte";
import { i18n, setLocale, t } from "@/i18n";
import { useRoute } from "@/router";
import { useAuthStore } from "@/stores/auth.svelte";
import { useGameStore } from "@/stores/game.svelte";
import HomeView from "@/views/HomeView.svelte";

const route = useRoute();
setLinguiContext(i18n);

const store = useGameStore();
const authStore = useAuthStore();
const connection = useGameConnection();
const settings = useSettingsPanel();
const announcer = useAnnouncer();

$effect(() => {
  const locale = store.localPlayerLocale;
  if (locale) void setLocale(locale);
});

onMount(() => {
  void (async () => {
    await authStore.bootstrap(store.localPlayerLocale, store.localPlayerName || null);
    if (authStore.currentUser?.preferredLocale) {
      store.setLocalPlayerLocale(authStore.currentUser.preferredLocale);
    }
    if (authStore.currentUser?.displayName && !store.localPlayerName) {
      store.localPlayerName = authStore.currentUser.displayName;
    }
  })();
});
</script>

  <div id="app">
    <HdIconButton class="app-settings-btn" label={$translate({ id: "settings.title", message: "Settings" })} onclick={() => settings.open()}>
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

    {#if route.name === "room"}
      {#await import("@/views/RoomView.svelte") then view}
        <view.default />
      {/await}
    {:else if route.name === "design-system"}
      {#await import("@/views/DesignSystemView.svelte") then view}
        <view.default />
      {/await}
    {:else}
      <HomeView />
    {/if}
    <!-- Non-blocking reconnect banner: shown when an established session drops and
         is auto-recovering, so the game view stays mounted (canvas/state intact). -->

      {#if connection.connectionStatus === 'reconnecting' && store.hydrated}<div transition:fade={{duration: 200}} class="reconnect-banner" role="status">
        <span class="reconnect-banner__spinner" aria-hidden="true"></span>
        {t("common.reconnecting")}
      </div>
    {/if}
    <HdToast />
    <div class="sr-only" role="status" aria-atomic="true">{announcer.message}</div>
    <SettingsPanel bind:open={() => settings.isOpen, (value) => { settings.isOpen = value; }} />
  </div>

<style>
#app {
  width: 100%;
  min-height: 100vh;
}
:global(.app-settings-btn) {
  position: fixed;
  /* Match the page gutter (~20px) so the gear sits in line with other UI
     rather than crowding the viewport edges. */
  top: max(20px, env(safe-area-inset-top));
  right: max(20px, env(safe-area-inset-right));
  z-index: 50;
}
:global(.reconnect-banner) {
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
:global(.reconnect-banner__spinner) {
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
/* No spinning for reduced motion: a slow fade still shows it is working. */
@media (prefers-reduced-motion: reduce) {
  :global(.reconnect-banner__spinner) {
    animation: reconnect-pulse 2s ease-in-out infinite;
  }
}
@keyframes reconnect-pulse {
  50% {
    opacity: 0.4;
  }
}
</style>
