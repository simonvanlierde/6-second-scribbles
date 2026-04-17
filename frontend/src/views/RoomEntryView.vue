<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, useTemplateRef } from "vue";
import { useRoute, useRouter } from "vue-router";

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
const router = useRouter();
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
const nameDialogRef = useTemplateRef<HTMLDialogElement>("nameDialogRef");
const playerNameDraft = ref(store.localPlayerName);
const isSubmitting = ref(false);
let missingRoomTimer: ReturnType<typeof setTimeout> | null = null;

const hasName = computed(() => playerNameDraft.value.trim().length > 0);
const isInProgress = computed(() => roomPhase.value === "drawing" || roomPhase.value === "guessing");
const showPreview = computed(() => roomExists.value && !statusError.value && !isInvalidCode.value);
const showGuestCard = computed(() => !statusError.value && (!roomExists.value || isInvalidCode.value || hasName.value));
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

function openNamePrompt() {
  if (!nameDialogRef.value?.open) {
    nameDialogRef.value?.showModal();
  }
}

function cancelNamePrompt() {
  nameDialogRef.value?.close();
  leaveRoom();
}

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
    statusError.value = null;
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
      nameDialogRef.value?.close();
      await nextTick();
      scheduleReturnToLobby();
      return;
    }

    connect(roomCode.value, { observeOnly: true });
    await nextTick();
    openNamePrompt();
  } catch {
    statusError.value = "We couldn't load this room right now.";
  } finally {
    isLoadingRoom.value = false;
  }
}

function submitNamePrompt() {
  const name = playerNameDraft.value.trim();
  if (!name) return;

  store.localPlayerName = name;
  nameDialogRef.value?.close();
  joinRoom();
}

function joinRoom() {
  const name = playerNameDraft.value.trim();
  if (!name || isSubmitting.value || !roomExists.value) return;

  isSubmitting.value = true;
  store.setRoomCodeAndSave(roomCode.value);

  if (isInProgress.value) {
    store.localPlayerName = name;
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
      v-if="showGuestCard"
      class="guest-card relative z-10 w-full max-w-[640px] rounded-3xl border border-white/10 bg-[rgba(10,12,28,0.78)] p-8 text-white shadow-[0_24px_80px_rgba(0,0,0,0.28)] backdrop-blur-[14px]"
    >
      <p class="m-0 mb-2 text-xs tracking-widest text-white/70 uppercase">Room {{ roomCode }}</p>
      <h1 v-if="isLoadingRoom" class="m-0">{{ $t('roomEntry.checkingRoom') }}</h1>
      <h1 v-else-if="statusError" class="m-0">{{ statusError }}</h1>
      <h1 v-else-if="isInvalidCode" class="m-0">{{ $t('roomEntry.invalidCode') }}</h1>
      <h1 v-else-if="roomExists" class="m-0">{{ phaseLabel }}</h1>
      <h1 v-else class="m-0">{{ $t('roomEntry.roomNotFound') }}</h1>

      <p v-if="!isLoadingRoom && !statusError && roomExists" class="mt-3 mb-0 text-white/85">
        <span v-if="isInProgress">{{ $t('roomEntry.roomInProgress') }}</span>
        <span v-else> {{ `${roomPlayerCount} ${roomPlayerCount === 1 ? 'player' : 'players'}` }} in room </span>
      </p>
      <p v-else-if="!isLoadingRoom && !statusError && isInvalidCode" class="mt-3 mb-0 text-white/85">
        {{ $t('roomEntry.invalidCodeText') }}
      </p>
      <p v-else-if="!isLoadingRoom && !statusError && !roomExists" class="mt-3 mb-0 text-white/85">
        {{ $t('roomEntry.roomNotExist') }}
      </p>
      <p v-else-if="statusError" class="mt-3 mb-0 text-white/85">{{ $t('roomEntry.tryGoBack') }}</p>

      <div class="mt-6 flex flex-wrap gap-3">
        <button
          type="button"
          class="cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
          @click="leaveRoom"
        >
          {{ $t('roomEntry.backToLobby') }}
        </button>
        <button
          v-if="roomExists"
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

    <dialog
      v-show="roomExists && !statusError && !isInvalidCode"
      ref="nameDialogRef"
      class="name-dialog fixed top-1/2 left-1/2 z-10 w-[min(92vw,420px)] -translate-x-1/2 -translate-y-1/2 rounded-[20px] border-0 bg-[rgba(10,12,28,0.95)] p-0 text-white shadow-[0_30px_90px_rgba(0,0,0,0.4)] backdrop:bg-black/55"
      @cancel.prevent="cancelNamePrompt"
    >
      <form class="name-form grid gap-3 p-6" method="dialog" @submit.prevent="submitNamePrompt">
        <h2 class="m-0">{{ $t('roomEntry.enterYourName') }}</h2>
        <p class="m-0">{{ $t('roomEntry.needNameText') }}</p>
        <input
          v-model="playerNameDraft"
          type="text"
          maxlength="20"
          :placeholder="$t('roomEntry.yourName')"
          class="name-input rounded-2xl border border-white/15 bg-white/5 px-4 py-3.5 text-inherit text-white"
          @keyup.enter="submitNamePrompt"
        >
        <div class="flex justify-end gap-3">
          <button
            type="button"
            class="cursor-pointer rounded-xl border-0 bg-white/10 px-4 py-3.5 font-extrabold text-white"
            @click="cancelNamePrompt"
          >
            {{ $t('roomEntry.back') }}
          </button>
          <button
            type="submit"
            class="cursor-pointer rounded-xl border-0 bg-gradient-to-br from-[#ffd166] to-[#ff8e72] px-4 py-3.5 font-extrabold text-[#1e1e1e] disabled:cursor-not-allowed disabled:opacity-55"
            :disabled="!hasName"
          >
            {{ $t('roomEntry.continue') }}
          </button>
        </div>
      </form>
    </dialog>
  </div>
</template>
