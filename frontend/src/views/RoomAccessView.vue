<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

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
const helperText = computed(() => {
  if (statusError.value) return i18n.global.t("roomAccess.loadFailed");
  if (isInvalidCode.value) return i18n.global.t("roomEntry.invalidCodeText");
  if (!roomExists.value) return i18n.global.t("roomAccess.roomDoesNotExist");
  if (isInProgress.value)
    return roomPhase.value === "drawing" || roomPhase.value === "guessing"
      ? i18n.global.t("roomEntry.roomInProgress")
      : "";
  return i18n.global.t("roomEntry.playersInRoom", { count: roomPlayerCount.value });
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
  store.setRoomCodeAndSave(roomCode.value);

  if (observeOnly) {
    store.setSpectatorMode(true);
    connect(roomCode.value, { observeOnly: true });
  } else {
    store.setSpectatorMode(false);
    store.setLocalPlayerAndSave(getOrCreatePlayerId(), name);
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
  <div
    class="grid min-h-screen place-items-center gap-4 px-6 py-8"
    style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%)"
  >
    <div
      class="relative z-10 w-full max-w-[640px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] p-8 text-white shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <p class="m-0 mb-2 text-xs tracking-widest text-white/70 uppercase">
        {{ $t("common.roomCode", { code: roomCode }) }}
      </p>
      <h1 v-if="isLoadingRoom" class="m-0">{{ $t('roomEntry.checkingRoom') }}</h1>
      <h1 v-else-if="statusError" class="m-0">{{ statusError }}</h1>
      <h1 v-else-if="isInvalidCode" class="m-0">{{ $t('roomEntry.invalidCode') }}</h1>
      <h1 v-else-if="roomExists" class="m-0">{{ phaseLabel }}</h1>
      <h1 v-else class="m-0">{{ $t('roomEntry.roomNotFound') }}</h1>

      <p class="mt-3 mb-0 text-white/85">{{ helperText }}</p>

      <div v-if="roomExists && !isInvalidCode && !statusError" class="mt-6 grid gap-4">
        <label class="grid gap-2">
          <span class="text-sm font-semibold text-white/80">{{ $t('roomEntry.enterYourName') }}</span>
          <input
            v-model="playerNameDraft"
            type="text"
            maxlength="20"
            :placeholder="$t('roomEntry.yourName')"
            class="name-input rounded-2xl border border-white/15 bg-white/5 px-4 py-3.5 text-inherit text-white"
            @keyup.enter="handlePrimaryAction"
          >
        </label>

        <p
          v-if="isInProgress"
          class="m-0 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/85"
        >
          {{ $t('roomEntry.roomInProgress') }}
        </p>

        <p class="m-0 text-sm text-white/70">{{ $t('roomEntry.playersInRoom', { count: roomPlayerCount }) }}</p>

        <div class="flex flex-wrap gap-3">
          <button
            type="button"
            class="cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
            @click="leaveRoom"
          >
            {{ $t('roomEntry.back') }}
          </button>
          <button
            type="button"
            class="cursor-pointer rounded-xl border-0 bg-gradient-to-br from-[#ffd166] to-[#ff8e72] px-4 py-3.5 font-extrabold text-[#1e1e1e] disabled:cursor-not-allowed disabled:opacity-55"
            :disabled="!hasName || isLoadingRoom || !!statusError || isSubmitting"
            @click="handlePrimaryAction"
          >
            {{ primaryActionLabel }}
          </button>
        </div>
      </div>

      <div v-else class="mt-6 flex flex-wrap gap-3">
        <div v-if="isInvalidCode" class="grid gap-2">
          <p class="m-0 text-sm text-white/80">{{ $t('roomEntry.invalidCodeText') }}</p>
        </div>
        <div v-else-if="statusError" class="grid gap-2">
          <p class="m-0 text-sm text-white/80">{{ $t('roomEntry.tryGoBack') }}</p>
        </div>
        <div v-else-if="!roomExists" class="grid gap-2">
          <p class="m-0 text-sm text-white/80">{{ $t('roomEntry.roomNotExist') }}</p>
        </div>
        <button
          type="button"
          class="cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
          @click="leaveRoom"
        >
          {{ $t('roomEntry.backToLobby') }}
        </button>
      </div>
    </div>
  </div>
</template>
