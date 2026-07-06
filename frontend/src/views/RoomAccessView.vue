<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import HdButton from "@/components/ui/HdButton.vue";
import HdCard from "@/components/ui/HdCard.vue";
import HdInput from "@/components/ui/HdInput.vue";
import HdPill from "@/components/ui/HdPill.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { RoomStatusResponseSchema } from "@/generated/api";
import { i18n } from "@/i18n";
import { apiRequest } from "@/lib/api";
import { normalizeGamePhase } from "@/shared/gamePhase";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import type { GamePhase } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const route = useRoute();
const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();

const rawRoomCode = computed(() => String(route.params.roomCode || ""));
const roomCode = computed(() => normalizeRoomCode(rawRoomCode.value));
const isInvalidCode = computed(() => !isValidRoomCode(roomCode.value));
const roomExists = ref(false);
const roomPlayerCount = ref(0);
const roomPhase = ref<GamePhase | null>(null);
const isLoadingRoom = ref(false);
const statusError = ref<string | null>(null);
const playerNameDraft = ref(store.localPlayerName);
const isSubmitting = ref(false);
let requestVersion = 0;

const hasName = computed(() => playerNameDraft.value.trim().length > 0);
const isInProgress = computed(() => roomPhase.value === "drawing" || roomPhase.value === "guessing");
const phaseLabel = computed(() => {
  switch (roomPhase.value) {
    case "lobby":
      return i18n.global.t("roomAccess.lobby");
    case "drawing":
    case "guessing":
      return i18n.global.t("roomAccess.gameInProgress");
    case "round_results":
      return i18n.global.t("roomAccess.roundResults");
    case "final_results":
      return i18n.global.t("roomAccess.finalResults");
    default:
      return i18n.global.t("roomEntry.checkingRoom");
  }
});
// Body copy for terminal states (invalid / missing / failed) — the joinable
// state renders its own pieces (player count pill, in-progress note) instead.
const terminalBody = computed(() => {
  if (statusError.value) return i18n.global.t("roomEntry.tryGoBack");
  if (isInvalidCode.value) return i18n.global.t("roomEntry.invalidCodeText");
  return i18n.global.t("roomAccess.roomDoesNotExist");
});
const primaryActionLabel = computed(() =>
  isSubmitting.value
    ? i18n.global.t("roomAccess.connecting")
    : isInProgress.value
      ? i18n.global.t("roomAccess.watchRoom")
      : i18n.global.t("roomAccess.joinRoom"),
);

async function loadRoomStatus(nextRoomCode: string) {
  const version = ++requestVersion;
  isLoadingRoom.value = true;
  statusError.value = null;
  roomExists.value = false;
  roomPlayerCount.value = 0;
  roomPhase.value = null;

  if (!nextRoomCode || isInvalidCode.value) {
    isLoadingRoom.value = false;
    return;
  }

  try {
    const data = await apiRequest(`/api/rooms/${nextRoomCode}/status`, {
      schema: RoomStatusResponseSchema,
    });

    if (version !== requestVersion) return;

    roomExists.value = Boolean(data.exists);
    roomPlayerCount.value = typeof data.players === "number" ? data.players : 0;
    roomPhase.value = normalizeGamePhase(data.game_phase);
  } catch {
    if (version !== requestVersion) return;
    statusError.value = i18n.global.t("roomAccess.loadFailed");
  } finally {
    if (version === requestVersion) {
      isLoadingRoom.value = false;
    }
  }
}

watch(
  roomCode,
  (nextRoomCode) => {
    void loadRoomStatus(nextRoomCode);
  },
  { immediate: true },
);

function leaveRoom() {
  router.push({ name: "home" });
}

function connectToRoom(observeOnly = false) {
  const name = playerNameDraft.value.trim();
  if (!name || isSubmitting.value || !roomExists.value || !roomCode.value) return;

  isSubmitting.value = true;
  store.localPlayerName = name;
  store.setRoomCode(roomCode.value);

  if (observeOnly) {
    store.setSpectatorMode(true);
    connect(roomCode.value, { observeOnly: true });
  } else {
    store.setSpectatorMode(false);
    store.setLocalPlayer(getOrCreatePlayerId(), name);
    connect(roomCode.value);
  }

  isSubmitting.value = false;
}

function handlePrimaryAction() {
  connectToRoom(isInProgress.value);
}

onBeforeUnmount(() => {
  requestVersion++;
});
</script>

<template>
  <div class="access-page">
    <HdCard class="access-card">
      <span class="access-code">
        <span class="access-code__label">{{ $t('home.roomCodeLabel') }}</span>
        <span class="access-code__value">{{ roomCode }}</span>
      </span>

      <h1 v-if="isLoadingRoom" class="access-title">{{ $t('roomEntry.checkingRoom') }}</h1>
      <h1 v-else-if="statusError" class="access-title">{{ statusError }}</h1>
      <h1 v-else-if="isInvalidCode" class="access-title">{{ $t('roomEntry.invalidCode') }}</h1>
      <h1 v-else-if="roomExists" class="access-title">{{ phaseLabel }}</h1>
      <h1 v-else class="access-title">{{ $t('roomEntry.roomNotFound') }}</h1>

      <template v-if="roomExists && !isInvalidCode && !statusError">
        <HdPill class="access-players">{{ $t('roomEntry.playersInRoom', { count: roomPlayerCount }) }}</HdPill>

        <HdCard v-if="isInProgress" variant="postit" class="access-note"> {{ $t('roomEntry.roomInProgress') }} </HdCard>

        <!-- biome-ignore lint/a11y/noLabelWithoutControl: wraps HdInput, which renders the text input, plus its visible label text -->
        <label class="access-name">
          <span class="access-name__label">{{ $t('roomEntry.enterYourName') }}</span>
          <HdInput
            v-model="playerNameDraft"
            class="name-input"
            maxlength="20"
            :placeholder="$t('roomEntry.yourName')"
            @keyup.enter="handlePrimaryAction"
          />
        </label>

        <div class="access-actions">
          <HdButton variant="secondary" @click="leaveRoom">{{ $t('roomEntry.back') }}</HdButton>
          <HdButton
            variant="primary"
            :disabled="!hasName || isLoadingRoom || !!statusError || isSubmitting"
            @click="handlePrimaryAction"
          >
            {{ primaryActionLabel }}
          </HdButton>
        </div>
      </template>

      <template v-else-if="!isLoadingRoom">
        <p class="access-body">{{ terminalBody }}</p>
        <div class="access-actions">
          <HdButton variant="secondary" @click="leaveRoom">{{ $t('roomEntry.backToHome') }}</HdButton>
        </div>
      </template>
    </HdCard>
  </div>
</template>

<style scoped>
.access-page {
  min-height: 100svh;
  display: grid;
  place-items: center;
  padding: 24px 20px;
  position: relative;
  z-index: 1;
}
.access-card {
  width: 100%;
  max-width: 440px;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-6);
}
.access-code {
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
.access-code__label {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  opacity: 0.7;
}
.access-code__value {
  font-family: var(--font-mono);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.3em;
}
.access-title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-display-sm);
  line-height: 1.15;
  margin: 0;
  color: var(--color-ink);
}
.access-players {
  align-self: flex-start;
}
.access-note {
  margin: 0;
}
.access-name {
  display: grid;
  gap: var(--space-2);
}
.access-name__label {
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  color: var(--color-ink-muted);
}
.access-body {
  font-family: var(--font-body);
  font-size: var(--text-body-lg);
  color: var(--color-ink-muted);
  margin: 0;
}
.access-actions {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  flex-wrap: wrap;
}
.access-actions > :only-child {
  margin-left: auto;
  margin-right: auto;
}
</style>
