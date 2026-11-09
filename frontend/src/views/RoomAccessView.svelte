<script lang="ts">
import { onDestroy, untrack } from "svelte";
import HdButton from "@/components/ui/HdButton.svelte";
import HdCard from "@/components/ui/HdCard.svelte";
import HdInput from "@/components/ui/HdInput.svelte";
import HdPill from "@/components/ui/HdPill.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { RoomStatusResponseSchema } from "@/generated/api";
import { t } from "@/i18n";
import { apiRequest } from "@/lib/api";
import { useRoute, useRouter } from "@/router";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import type { GamePhase } from "@/shared/types";
import { useGameStore } from "@/stores/game.svelte";

const route = useRoute();
const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();

const rawRoomCode = $derived(String(route.params.roomCode || ""));
const roomCode = $derived(normalizeRoomCode(rawRoomCode));
const isInvalidCode = $derived(!isValidRoomCode(roomCode));
let roomExists = $state(false);
let roomPlayerCount = $state(0);
let roomPhase = $state<GamePhase | null>(null);
let isLoadingRoom = $state(false);
let statusError = $state<string | null>(null);
let playerNameDraft = $state(store.localPlayerName);
let isSubmitting = $state(false);
let requestVersion = 0;

const hasName = $derived(playerNameDraft.trim().length > 0);
const isInProgress = $derived(roomPhase === "drawing" || roomPhase === "guessing");
const phaseLabel = $derived.by(() => {
  switch (roomPhase) {
    case "lobby":
      return t("roomAccess.lobby");
    case "drawing":
    case "guessing":
      return t("roomAccess.gameInProgress");
    case "round_results":
      return t("roomAccess.roundResults");
    case "final_results":
      return t("roomAccess.finalResults");
    default:
      return t("roomEntry.checkingRoom");
  }
});
// Body copy for terminal states (invalid / missing / failed) — the joinable
// state renders its own pieces (player count pill, in-progress note) instead.
const terminalBody = $derived.by(() => {
  if (statusError) return t("roomEntry.tryGoBack");
  if (isInvalidCode) return t("roomEntry.invalidCodeText");
  return t("roomAccess.roomDoesNotExist");
});
const primaryActionLabel = $derived(
  isSubmitting ? t("roomAccess.connecting") : isInProgress ? t("roomAccess.watchRoom") : t("roomAccess.joinRoom"),
);

async function loadRoomStatus(nextRoomCode: string) {
  const version = ++requestVersion;
  isLoadingRoom = true;
  statusError = null;
  roomExists = false;
  roomPlayerCount = 0;
  roomPhase = null;

  if (!nextRoomCode || isInvalidCode) {
    isLoadingRoom = false;
    return;
  }

  try {
    const data = await apiRequest(`/api/rooms/${nextRoomCode}/status`, {
      schema: RoomStatusResponseSchema,
    });

    if (version !== requestVersion) return;

    roomExists = Boolean(data.exists);
    roomPlayerCount = typeof data.players === "number" ? data.players : 0;
    roomPhase = data.game_phase ?? "lobby";
  } catch {
    if (version !== requestVersion) return;
    statusError = t("roomAccess.loadFailed");
  } finally {
    if (version === requestVersion) {
      isLoadingRoom = false;
    }
  }
}

$effect(() => {
  const nextRoomCode = roomCode;
  untrack(() => {
    void loadRoomStatus(nextRoomCode);
  });
});

function leaveRoom() {
  router.push({ name: "home" });
}

function connectToRoom(observeOnly = false) {
  const name = playerNameDraft.trim();
  if (!name || isSubmitting || !roomExists || !roomCode) return;

  isSubmitting = true;
  store.localPlayerName = name;
  store.setRoomCode(roomCode);

  if (observeOnly) {
    store.setSpectatorMode(true);
    connect(roomCode, { observeOnly: true });
  } else {
    store.setSpectatorMode(false);
    store.setLocalPlayer(getOrCreatePlayerId(), name);
    connect(roomCode);
  }

  isSubmitting = false;
}

function handlePrimaryAction() {
  connectToRoom(isInProgress);
}

onDestroy(() => {
  requestVersion++;
});
</script>

  <main class="access-page">
    <HdCard class="access-card">
      <span class="access-code">
        <span class="access-code__label">{t('home.roomCodeLabel')}</span>
        <span class="access-code__value">{roomCode}</span>
      </span>

      {#if isLoadingRoom}<h1 class="access-title">{t('roomEntry.checkingRoom')}</h1>
      {:else if statusError}<h1 class="access-title">{statusError}</h1>
      {:else if isInvalidCode}<h1 class="access-title">{t('roomEntry.invalidCode')}</h1>
      {:else if roomExists}<h1 class="access-title">{phaseLabel}</h1>
      {:else}<h1 class="access-title">{t('roomEntry.roomNotFound')}</h1>

      {/if}{#if roomExists && !isInvalidCode && !statusError}
        <HdPill class="access-players">{t('roomEntry.playersInRoom', { count: roomPlayerCount })}</HdPill>

        {#if isInProgress}<HdCard variant="postit" class="access-note"> {t('roomEntry.roomInProgress')} </HdCard>

        <!-- biome-ignore lint/a11y/noLabelWithoutControl: wraps HdInput, which renders the text input, plus its visible label text -->
        {/if}<label class="access-name">
          <span class="access-name__label">{t('roomEntry.enterYourName')}</span>
          <HdInput
            bind:modelValue={playerNameDraft}
            class="name-input"
            maxlength={20}
            placeholder={t('roomEntry.yourName')}
            onkeyup={(event: KeyboardEvent) => { if (event.key === "Enter") handlePrimaryAction(); }}
          />
        </label>

        <div class="access-actions">
          <HdButton variant="secondary" onclick={leaveRoom}>{t('roomEntry.back')}</HdButton>
          <HdButton
            variant="primary"
            disabled={!hasName || isLoadingRoom || !!statusError || isSubmitting}
            onclick={handlePrimaryAction}
          >
            {primaryActionLabel}
          </HdButton>
        </div>


      {:else if !isLoadingRoom}
        <p class="access-body">{terminalBody}</p>
        <div class="access-actions">
          <HdButton variant="secondary" onclick={leaveRoom}>{t('roomEntry.backToHome')}</HdButton>
        </div>

    {/if}</HdCard>
  </main>

<style>
:global(.access-page) {
  min-height: 100svh;
  display: grid;
  place-items: center;
  padding: 24px 20px;
  position: relative;
  z-index: 1;
}
:global(.access-card) {
  width: 100%;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-6);
}
:global(.access-code) {
  align-self: flex-start;
  display: inline-flex;
  align-items: baseline;
  gap: 10px;
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
  border: 2px dashed var(--color-ink);
  border-radius: 12px 18px 14px 22px;
  padding: 4px 14px;
}
:global(.access-code__label) {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  opacity: 0.7;
}
:global(.access-code__value) {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.3em;
}
:global(.access-title) {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-display-sm);
  line-height: 1.15;
  margin: 0;
  color: var(--color-ink);
}
:global(.access-players) {
  align-self: flex-start;
}
:global(.access-note) {
  margin: 0;
}
:global(.access-name) {
  display: grid;
  gap: var(--space-2);
}
:global(.access-name__label) {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  color: var(--color-ink-muted);
}
:global(.access-body) {
  font-family: var(--font-body);
  font-size: var(--text-body-lg);
  color: var(--color-ink-muted);
  margin: 0;
}
:global(.access-actions) {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}
:global(.access-actions) > :only-child {
  margin-left: auto;
  margin-right: auto;
}
</style>
