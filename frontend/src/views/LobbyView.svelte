<script lang="ts">
import GameSettingsPanel from "@/components/GameSettingsPanel.svelte";
import LeaveRoomDialog from "@/components/LeaveRoomDialog.svelte";
import PlayerListPanel from "@/components/PlayerListPanel.svelte";
import SharedDrawpad from "@/components/SharedDrawpad.svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdIconButton from "@/components/ui/HdIconButton.svelte";
import HdToggle from "@/components/ui/HdToggle.svelte";
import { useNotifications } from "@/composables/notifications.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { GAME_SETTINGS } from "@/config/gameConfig";
import { t } from "@/i18n";
import { useRoute } from "@/router";
import { useGameStore } from "@/stores/game.svelte";

const route = useRoute();
const store = useGameStore();
const { send } = useGameConnection();
const { showNotification } = useNotifications();

let leaveDialog: { request(): void } | undefined = $state();

const localPadVisible = $derived(store.localPadVisible);

const roomCode = $derived(route.params.roomCode as string);
const playerCount = $derived(store.playersList.length);
const canStart = $derived(store.canStartGame && store.isHost);

function togglePrivacy() {
  if (store.isHost) {
    send({ type: "privacy_changed", isPrivate: store.isPrivateRoom });
  }
}

function handleClear() {
  if (store.isHost) {
    store.clearStrokes();
    send({ type: "drawpad_clear" });
  }
}

function toggleDrawpad() {
  store.setLocalPadVisible(!localPadVisible);
}

function startGame() {
  if (!canStart) return;
  send({
    type: "start_game",
    difficulty: store.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
    rounds: store.maxRounds || GAME_SETTINGS.rounds.DEFAULT,
    drawingTimeLimit: store.drawingTimeLimit || GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT,
    guessingTimeLimit: store.guessingTimeLimit || GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT,
  });
}

async function copyRoomCode() {
  try {
    await navigator.clipboard.writeText(roomCode);
  } catch {
    return; // no clipboard access (insecure context or denied permission)
  }
  showNotification(t("common.copied"));
}

function toggleRoomPadVisibility() {
  const visible = !store.roomPadVisible;
  store.setRoomPadVisible(visible);
  send({ type: "pad_visibility", visible });
}
</script>

  <main class="lobby-page">
    <h1 class="sr-only">{t('roomAccess.lobby')}</h1>
    <div class="lobby-topbar">
      <HdButton variant="secondary" onclick={() => leaveDialog?.request()}> ← {t('lobby.leaveRoom')} </HdButton>
      <button type="button" class="lobby-code" title={t('common.copyRoomCode')} onclick={copyRoomCode}>
        <span class="lobby-code__label">{t('home.roomCodeLabel')}</span>
        <span class="lobby-code__value">{roomCode}</span>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      </button>
    </div>

    <div class="lobby-grid">
      <HdCard class="lobby-main">
        <div class="lobby-main__head">
          <h2 class="lobby-main__title">{t('lobby.players', { count: playerCount })}</h2>
          {#if store.isHost}<HdToggle
            bind:modelValue={() => store.isPrivateRoom, (value) => store.setPrivacy(value)}
            label={t('settings.privateRoom')}
            help={t('settings.privateRoomHelp')}
            onchange={togglePrivacy}
          />
        {/if}</div>
        <PlayerListPanel />

        <div class="lobby-main__settings"><GameSettingsPanel /></div>

        {#if store.isHost}<HdButton
          variant="primary"
          class="lobby-main__start"
          disabled={!canStart}
          onclick={startGame}
        >
          {canStart ? t('lobby.startGame') : t('lobby.waitingForPlayers')}
        </HdButton>
        {:else}<HdCard variant="postit" class="lobby-main__waiting">
          {playerCount >= 2 ? t('lobby.waitingForHost') : t('lobby.waitingForMore')}
        </HdCard>
      {/if}</HdCard>

      {#if store.isHost || store.roomPadVisible}<HdCard class="lobby-drawpad">
        <div class="lobby-drawpad__head">
          <h3 class="lobby-drawpad__title">{t('lobby.doodleTitle')}</h3>

          {#if store.isHost}<div class="lobby-drawpad__controls">
            <!-- Everyone: host controls that affect all players -->
            <div class="ctrl-group">
              <span class="ctrl-group__badge" aria-hidden="true">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </span>
              <HdIconButton variant="ghost" label={t('lobby.clearForAll')} onclick={handleClear}>
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3 6h18" />
                  <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  <path d="M6 6l1 14a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-14" />
                </svg>
              </HdIconButton>
              <HdIconButton
                variant="ghost"
                label={store.roomPadVisible ? t('lobby.hideForAll') : t('lobby.showForAll')}
                onclick={toggleRoomPadVisibility}
              >
                {#if store.roomPadVisible}<svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 7 10 7a13.4 13.4 0 0 1-1.67 2.68" />
                  <path d="M6.61 6.61A13.5 13.5 0 0 0 2 11s3.5 7 10 7a9.7 9.7 0 0 0 5.39-1.61" />
                  <path d="M14.12 14.12A3 3 0 1 1 9.88 9.88" />
                  <path d="M2 2l20 20" />
                </svg>
                {:else}<svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              {/if}</HdIconButton>
            </div>

            <!-- You: the host's own pad visibility -->
            {#if store.roomPadVisible}<div class="ctrl-group">
              <span class="ctrl-group__badge" aria-hidden="true">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </span>
              <HdIconButton
                variant="ghost"
                label={localPadVisible ? t('lobby.hideMyPad') : t('lobby.showMyPad')}
                onclick={toggleDrawpad}
              >
                {#if localPadVisible}<svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 7 10 7a13.4 13.4 0 0 1-1.67 2.68" />
                  <path d="M6.61 6.61A13.5 13.5 0 0 0 2 11s3.5 7 10 7a9.7 9.7 0 0 0 5.39-1.61" />
                  <path d="M14.12 14.12A3 3 0 1 1 9.88 9.88" />
                  <path d="M2 2l20 20" />
                </svg>
                {:else}<svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  aria-hidden="true"
                >
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
              {/if}</HdIconButton>
            </div>
          {/if}</div>

          <!-- Non-host: just toggle their own pad -->
          {:else}<HdIconButton
            variant="ghost"
            label={localPadVisible ? t('lobby.hideMyPad') : t('lobby.showMyPad')}
            onclick={toggleDrawpad}
          >
            {#if localPadVisible}<svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c6.5 0 10 7 10 7a13.4 13.4 0 0 1-1.67 2.68" />
              <path d="M6.61 6.61A13.5 13.5 0 0 0 2 11s3.5 7 10 7a9.7 9.7 0 0 0 5.39-1.61" />
              <path d="M14.12 14.12A3 3 0 1 1 9.88 9.88" />
              <path d="M2 2l20 20" />
            </svg>
            {:else}<svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          {/if}</HdIconButton>
        {/if}</div>

        {#if store.roomPadVisible && localPadVisible}<div class="drawpad-canvas"><SharedDrawpad /></div>
      {/if}</HdCard>
    {/if}</div>

    <LeaveRoomDialog bind:this={leaveDialog} />
  </main>

<style>
:global(.lobby-page) {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  position: relative;
  z-index: 1;
}
:global(.lobby-topbar) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  /* Reserve space on the right so the room code clears the globally-fixed
     settings gear (App.svelte, position: fixed; top/right: 12px; z-index: 50). */
  padding-right: calc(var(--space-4) + 52px);
  margin-bottom: 24px;
  flex-wrap: wrap;
}
:global(.lobby-code) {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
  border: 2px dashed var(--color-ink);
  border-radius: 12px 18px 14px 22px;
  padding: 6px 14px;
  font-family: var(--font-mono);
  cursor: pointer;
  transition: transform var(--motion-fast) var(--ease-spring);
}
:global(.lobby-code):hover {
  transform: translateY(-1px);
}
:global(.lobby-code__label) {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
}
:global(.lobby-code__value) {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.3em;
}
:global(.lobby-grid) {
  display: grid;
  /* Settings only needs enough room for its content; give the rest to the
     drawpad so it isn't squeezed by wasted horizontal space. */
  grid-template-columns: minmax(300px, 500px) 1fr;
  gap: 20px;
  align-items: start;
}
@media (max-width: 900px) {
  :global(.lobby-grid) {
    grid-template-columns: 1fr;
  }
}
:global(.lobby-main) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
:global(.lobby-main__head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
:global(.lobby-main__title) {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
  color: var(--color-ink);
}
:global(.lobby-main__settings) {
  padding-top: 8px;
  border-top: 1px dashed var(--color-ink);
}
:global(.lobby-main__start) {
  margin-top: 8px;
}
:global(.lobby-main__waiting) {
  margin-top: 8px;
  text-align: center;
}
:global(.lobby-drawpad) {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
:global(.lobby-drawpad__head) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
:global(.lobby-drawpad__title) {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
}
:global(.lobby-drawpad__controls) {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}
/* Each cluster is led by a badge that labels its scope: people = everyone,
   single person = just you. */
:global(.ctrl-group) {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px 2px 4px;
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
  background: var(--color-card);
  box-shadow: var(--shadow-pill);
}
:global(.ctrl-group__badge) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  color: var(--color-ink-muted);
}
:global(.ctrl-group__badge) svg {
  width: 17px;
  height: 17px;
}
</style>
