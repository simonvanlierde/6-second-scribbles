<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute } from "vue-router";

import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { API_HOST } from "@/config/gameConfig";
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
const { leaveRoom } = useLeaveRoom();
const { connect } = useGameConnection();

const rawRoomCode = computed(() => String(route.params.roomCode || ""));
const roomCode = computed(() => normalizeRoomCode(rawRoomCode.value));
const isInvalidCode = computed(() => !isValidRoomCode(roomCode.value));
const roomExists = ref(false);
const roomPlayerCount = ref(0);
const roomPhase = ref<GamePhase | null>(null);
const isLoadingRoom = ref(false);
const statusError = ref<string | null>(null);
const nameDialogRef = ref<HTMLDialogElement | null>(null);
const playerNameDraft = ref(store.localPlayerName);
const isSubmitting = ref(false);
let missingRoomTimer: ReturnType<typeof setTimeout> | null = null;

const hasName = computed(() => playerNameDraft.value.trim().length > 0);
const isInProgress = computed(
	() => roomPhase.value === "drawing" || roomPhase.value === "guessing",
);
const showPreview = computed(
	() => roomExists.value && !statusError.value && !isInvalidCode.value,
);
const showGuestCard = computed(
	() =>
		!statusError.value &&
		(!roomExists.value || isInvalidCode.value || hasName.value),
);
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

	// If the room code is invalid, skip the status fetch and show an invalid-code UI.
	if (isInvalidCode.value) {
		statusError.value = null;
		roomExists.value = false;
		scheduleReturnToLobby();
		isLoadingRoom.value = false;
		return;
	}

	try {
		const response = await fetch(
			`${API_HOST}/api/rooms/${roomCode.value}/status`,
		);
		const data = await response.json();

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
  <div class="guest-screen">
    <component :is="previewView" v-if="showPreview" class="preview-room" />
    <div v-if="showGuestCard" class="guest-card">
      <p class="eyebrow">Room {{ roomCode }}</p>
      <h1 v-if="isLoadingRoom">{{ $t('roomEntry.checkingRoom') }}</h1>
      <h1 v-else-if="statusError">{{ statusError }}</h1>
      <h1 v-else-if="isInvalidCode">{{ $t('roomEntry.invalidCode') }}</h1>
      <h1 v-else-if="roomExists">{{ phaseLabel }}</h1>
      <h1 v-else>{{ $t('roomEntry.roomNotFound') }}</h1>

      <p v-if="!isLoadingRoom && !statusError && roomExists" class="status-copy">
        <span v-if="isInProgress"
          >{{ $t('roomEntry.roomInProgress') }}</span
        >
        <!-- For counts, use simple pluralization lookup -->
        <span v-else>{{ roomPlayerCount === 1 ? roomPlayerCount + " player" : roomPlayerCount + " players" }} in room</span>
      </p>
      <p v-else-if="!isLoadingRoom && !statusError && isInvalidCode" class="status-copy">
        {{ $t('roomEntry.invalidCodeText') }}
      </p>
      <p v-else-if="!isLoadingRoom && !statusError && !roomExists" class="status-copy">
        {{ $t('roomEntry.roomNotExist') }}
      </p>
      <p v-else-if="statusError" class="status-copy">{{ $t('roomEntry.tryGoBack') }}</p>

      <div class="actions">
        <button type="button" class="back-btn" @click="leaveRoom">{{ $t('roomEntry.backToLobby') }}</button>
        <button
          v-if="roomExists"
          type="button"
          class="join-btn"
          :disabled="!hasName || isLoadingRoom || !!statusError || isSubmitting"
          @click="joinRoom"
        >
          {{ isSubmitting ? $t('roomEntry.joining') : isInProgress ? $t('roomEntry.watchRoom') : $t('roomEntry.joinRoom') }}
        </button>
      </div>
    </div>

    <dialog
      v-show="roomExists && !statusError && !isInvalidCode"
      ref="nameDialogRef"
      class="name-dialog"
      @cancel.prevent="cancelNamePrompt"
    >
      <form class="name-form" method="dialog" @submit.prevent="submitNamePrompt">
        <h2>{{ $t('roomEntry.enterYourName') }}</h2>
        <p>{{ $t('roomEntry.needNameText') }}</p>
        <input
          v-model="playerNameDraft"
          type="text"
          maxlength="20"
          :placeholder="$t('roomEntry.yourName')"
          class="name-input"
          @keyup.enter="submitNamePrompt"
        >
        <div class="dialog-actions">
          <button type="button" class="back-btn" @click="cancelNamePrompt">{{ $t('roomEntry.back') }}</button>
          <button type="submit" class="join-btn" :disabled="!hasName">{{ $t('roomEntry.continue') }}</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<style scoped>
.guest-screen {
  min-height: 100vh;
  padding: 2rem 1.5rem;
  display: grid;
  place-items: center;
  gap: 1rem;
  background: var(--color-bg-gradient);
}

.guest-card {
  width: min(640px, 100%);
  padding: 2rem;
  border-radius: 24px;
  background: rgba(10, 12, 28, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
  color: white;
  backdrop-filter: blur(14px);
}

.preview-room {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

.eyebrow {
  margin: 0 0 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.72);
}

h1 {
  margin: 0;
}

.status-copy {
  margin: 0.75rem 0 0;
  color: rgba(255, 255, 255, 0.86);
}

.actions {
  margin-top: 1.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.back-btn,
.join-btn {
  border: 0;
  border-radius: 14px;
  padding: 0.85rem 1rem;
  font-weight: 800;
  cursor: pointer;
}

.back-btn {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.join-btn {
  background: linear-gradient(135deg, #ffd166, #ff8e72);
  color: #1e1e1e;
}

.join-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.name-dialog {
  border: 0;
  border-radius: 20px;
  padding: 0;
  background: rgba(10, 12, 28, 0.95);
  color: white;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.4);
  width: min(92vw, 420px);
  position: fixed;
  inset: auto;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
}

.name-dialog::backdrop {
  background: rgba(0, 0, 0, 0.55);
}

.name-form {
  padding: 1.5rem;
  display: grid;
  gap: 0.75rem;
}

.name-form h2,
.name-form p {
  margin: 0;
}

.name-input {
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  padding: 0.9rem 1rem;
  background: rgba(255, 255, 255, 0.06);
  color: white;
  font: inherit;
}

.guest-card {
  position: relative;
  z-index: 1;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
