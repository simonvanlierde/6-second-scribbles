<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";

import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { RoomStatusResponseSchema } from "@/generated/api";
import { apiRequest } from "@/lib/api";
import { normalizeGamePhase } from "@/shared/gamePhase";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import type { GamePhase } from "@/shared/types";
import { useGameStore } from "@/stores/game";
import LobbyView from "@/views/LobbyView.vue";
import ResultsView from "@/views/ResultsView.vue";
import RoundResultsView from "@/views/RoundResultsView.vue";
import SpectatorRoomView from "@/views/SpectatorRoomView.vue";

const route = useRoute();
const store = useGameStore();
const { connect } = useGameConnection();
const { leaveRoom } = useLeaveRoom();

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
let missingRoomTimer: ReturnType<typeof setTimeout> | null = null;

const hasName = computed(() => playerNameDraft.value.trim().length > 0);
const isInProgress = computed(() => roomPhase.value === "drawing" || roomPhase.value === "guessing");
const showPreview = computed(() => roomExists.value && !statusError.value && !isInvalidCode.value);
const previewView = computed(() =>
  roomPhase.value === "lobby"
    ? LobbyView
    : roomPhase.value === "round_results"
      ? RoundResultsView
      : roomPhase.value === "final_results"
        ? ResultsView
        : SpectatorRoomView,
);
const phaseLabel = computed(() => {
  switch (roomPhase.value) {
    case "lobby":
      return "Lobby";
    case "drawing":
      return "Game in progress";
    case "guessing":
      return "Game in progress";
    case "round_results":
      return "Round results";
    case "final_results":
      return "Final results";
    default:
      return "Checking room";
  }
});
const helperText = computed(() => {
  if (statusError.value) return "We couldn't load this room right now.";
  if (isInvalidCode.value) return "That room code doesn't look valid.";
  if (!roomExists.value) return "This room does not exist, bringing you back to the lobby...";
  if (isInProgress.value) return "Enter a name to watch live now. You can join once the room returns to the lobby.";
  return `${roomPlayerCount.value} ${roomPlayerCount.value === 1 ? "player" : "players"} in room`;
});

function scheduleReturnToLobby() {
  if (missingRoomTimer) clearTimeout(missingRoomTimer);
  missingRoomTimer = setTimeout(() => {
    leaveRoom();
  }, 5000);
}

async function loadRoomStatus() {
  isLoadingRoom.value = true;
  statusError.value = null;
  if (missingRoomTimer) clearTimeout(missingRoomTimer);

  if (isInvalidCode.value) {
    roomExists.value = false;
    scheduleReturnToLobby();
    isLoadingRoom.value = false;
    return;
  }

  try {
    const data = await apiRequest(`/api/rooms/${roomCode.value}/status`, {
      schema: RoomStatusResponseSchema,
    });

    roomExists.value = Boolean(data.exists);
    roomPlayerCount.value = typeof data.players === "number" ? data.players : 0;
    roomPhase.value = normalizeGamePhase(data.game_phase);

    if (!roomExists.value) {
      await nextTick();
      scheduleReturnToLobby();
      return;
    }

    connect(roomCode.value, { observeOnly: true });
  } catch {
    statusError.value = "We couldn't load this room right now.";
  } finally {
    isLoadingRoom.value = false;
  }
}

function joinRoom() {
  const name = playerNameDraft.value.trim();
  if (!name || isSubmitting.value || !roomExists.value) return;

  isSubmitting.value = true;
  store.localPlayerName = name;
  store.setRoomCodeAndSave(roomCode.value);

  if (isInProgress.value) {
    store.setSpectatorMode(true);
    connect(roomCode.value, { observeOnly: true });
    isSubmitting.value = false;
    return;
  }

  store.setSpectatorMode(false);
  store.setLocalPlayerAndSave(getOrCreatePlayerId(), name);
  connect(roomCode.value);
  isSubmitting.value = false;
}

onMounted(() => {
  void loadRoomStatus();
});

onUnmounted(() => {
  if (missingRoomTimer) clearTimeout(missingRoomTimer);
});
</script>

<template>
  <div
    class="grid min-h-screen place-items-center gap-4 px-6 py-8"
    style="background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-secondary) 100%)"
  >
    <component :is="previewView" v-if="showPreview" class="preview-room fixed inset-0 z-0 pointer-events-none" />

    <div
      class="relative z-10 w-full max-w-[640px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] p-8 text-white shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <p class="m-0 mb-2 text-xs tracking-widest text-white/70 uppercase">Room {{ roomCode }}</p>
      <h1 v-if="isLoadingRoom" class="m-0">{{ $t('roomEntry.checkingRoom') }}</h1>
      <h1 v-else-if="statusError" class="m-0">{{ statusError }}</h1>
      <h1 v-else-if="isInvalidCode" class="m-0">{{ $t('roomEntry.invalidCode') }}</h1>
      <h1 v-else-if="roomExists" class="m-0">{{ phaseLabel }}</h1>
      <h1 v-else class="m-0">{{ $t('roomEntry.roomNotFound') }}</h1>

      <p class="mt-3 mb-0 text-white/85">{{ helperText }}</p>

      <div v-if="roomExists && !isInvalidCode && !statusError" class="mt-6 grid gap-3">
        <label class="grid gap-2">
          <span class="text-sm font-semibold text-white/80">{{ $t('roomEntry.enterYourName') }}</span>
          <input
            v-model="playerNameDraft"
            type="text"
            maxlength="20"
            :placeholder="$t('roomEntry.yourName')"
            class="name-input rounded-2xl border border-white/15 bg-white/5 px-4 py-3.5 text-inherit text-white"
            @keyup.enter="joinRoom"
          >
        </label>

        <div class="flex flex-wrap gap-3">
          <button
            type="button"
            class="cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
            @click="leaveRoom"
          >
            {{ $t('roomEntry.backToLobby') }}
          </button>
          <button
            type="button"
            class="cursor-pointer rounded-xl border-0 bg-gradient-to-br from-[#ffd166] to-[#ff8e72] px-4 py-3.5 font-extrabold text-[#1e1e1e] disabled:cursor-not-allowed disabled:opacity-55"
            :disabled="!hasName || isLoadingRoom || !!statusError || isSubmitting"
            @click="joinRoom"
          >
            {{ isSubmitting
                ? $t('roomEntry.joining')
                : isInProgress
                  ? $t('roomEntry.watchRoom')
                  : $t('roomEntry.joinRoom') }}
          </button>
        </div>
      </div>

      <div v-else class="mt-6 flex flex-wrap gap-3">
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
