<script lang="ts">
import { onDestroy, tick, untrack } from "svelte";
import { useAnnouncer } from "@/composables/useAnnouncer.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { t } from "@/i18n";
import { useRoute } from "@/router";
import { normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game.svelte";
import GameView from "@/views/GameView.svelte";
import LobbyView from "@/views/LobbyView.svelte";
import ResultsView from "@/views/ResultsView.svelte";
import RoomAccessView from "@/views/RoomAccessView.svelte";
import RoundResultsView from "@/views/RoundResultsView.svelte";
import SpectatorRoomView from "@/views/SpectatorRoomView.svelte";

const store = useGameStore();
const route = useRoute();
const connection = useGameConnection();
const { connect } = connection;
const routeRoomCode = $derived(normalizeRoomCode(String(route.params.roomCode || "")));
const inActiveRoom = $derived(Boolean(store.localPlayerId) && store.roomCode === routeRoomCode);

// Owning the (re)connect here — rather than in App.svelte's one-shot mount —
// is reliable: this view only renders once the room route is resolved, so the
// normalized room code and persisted identity are available. Covers reload /
// returning to a room; the connection layer auto-reconnects on later drops.
function ensureConnected() {
  if (inActiveRoom && connection.connectionStatus === "disconnected") {
    connect(routeRoomCode);
  }
}
$effect(() => {
  const active = inActiveRoom;
  untrack(() => {
    if (active) ensureConnected();
  });
});
const gamePhase = $derived(store.gamePhase);
const isSpectating = $derived(
  (!inActiveRoom && store.isSpectatorMode && gamePhase !== "lobby") ||
    (!inActiveRoom && (gamePhase === "drawing" || gamePhase === "guessing")),
);
// While we intend to be in this room but the server's authoritative snapshot has
// not yet been applied (initial load / reconnect after a reload), render a
// connecting state rather than a screen built from non-authoritative state.
const isConnecting = $derived(inActiveRoom && !store.hydrated);

const { announce } = useAnnouncer();
const defaultTitle = document.title;

const pageTitle = $derived.by(() => {
  if (isSpectating) return t("spectator.watchingRoom");
  if (!inActiveRoom) return t("roomAccess.joinRoom");
  if (isConnecting) return t("common.connecting");
  const round = store.currentRound;
  switch (gamePhase) {
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
$effect(() => {
  document.title = `${pageTitle} · ${t("home.title")}`;
});
onDestroy(() => {
  document.title = defaultTitle;
});

// A phase change swaps the whole screen, which would drop keyboard focus to <body>
// and say nothing to a screen reader: announce the new phase and focus its heading.
let previousPhase = store.gamePhase;
$effect(() => {
  const nextPhase = gamePhase;
  if (nextPhase === previousPhase) return;
  previousPhase = nextPhase;
  untrack(() => {
    if (!store.hydrated) return;
    announce(pageTitle);
    if (!inActiveRoom) return;
    void tick().then(() => {
      const heading = document.querySelector<HTMLElement>("main h1");
      if (!heading) return;
      heading.setAttribute("tabindex", "-1");
      heading.focus();
    });
  });
});
</script>

  {#if !inActiveRoom && !isSpectating}<RoomAccessView />
  {:else if isSpectating}<SpectatorRoomView />
  {:else if isConnecting}<main class="room-connecting">
    <div class="room-connecting__card">
      <span class="room-connecting__spinner" aria-hidden="true"></span>
      <h1 class="room-connecting__text">{t("common.connecting")}</h1>
    </div>
  </main>
  {:else if gamePhase === 'lobby'}<LobbyView />
  {:else if gamePhase === 'drawing' || gamePhase === 'guessing'}<GameView />
  {:else if gamePhase === 'round_results'}<RoundResultsView />
  {:else if gamePhase === 'final_results'}<ResultsView />
  {:else}<LobbyView />
{/if}
<style>
:global(.room-connecting) {
  display: flex;
  min-height: 100dvh;
  align-items: center;
  justify-content: center;
  background: var(--color-paper);
}
:global(.room-connecting__card) {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-display);
  font-size: var(--text-heading-sm);
  color: var(--color-ink);
}
:global(.room-connecting__text) {
  margin: 0;
  font-size: inherit;
}
:global(.room-connecting__spinner) {
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
  :global(.room-connecting__spinner) {
    animation: room-connecting-pulse 2s ease-in-out infinite;
  }
}
@keyframes room-connecting-pulse {
  50% {
    opacity: 0.4;
  }
}
</style>
