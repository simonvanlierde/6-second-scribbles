<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import LocaleSelector from "@/components/LocaleSelector.vue";
import RoomCodeInput from "@/components/RoomCodeInput.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { API_HOST } from "@/config/gameConfig";
import { getOrCreatePlayerId } from "@/shared/playerIdentity";
import { isValidRoomCode, normalizeRoomCode } from "@/shared/roomCode";
import { useGameStore } from "@/stores/game";

const router = useRouter();
const store = useGameStore();
const { connect } = useGameConnection();

const playerName = computed({
	get: () => store.localPlayerName,
	set: (value: string) => {
		store.localPlayerName = value;
	},
});
const playerLocale = computed({
	get: () => store.localPlayerLocale,
	set: (value: string) => {
		store.setLocalPlayerLocale(value);
	},
});
const roomCodeModel = ref("");
const joinBtnRef = ref<HTMLButtonElement | null>(null);
const isJoiningRandom = ref(false);
const isCheckingRoom = ref(false);
const howToPlayOpen = ref(false);
const { fetchLocaleAvailability, localeOptions } = useLocaleAvailability();

type Toast = {
	message: string;
	type: "error" | "info";
};
const toast = ref<Toast | null>(null);
let toastTimer: ReturnType<typeof setTimeout> | null = null;

onMounted(() => {
  void fetchLocaleAvailability();
});

watch(localeOptions, (options) => {
  const selected = options.find((option) => option.code === playerLocale.value);
  if (selected?.enabled) {
    return;
  }

  const fallback = options.find((option) => option.enabled);
  if (fallback) {
    store.setLocalPlayerLocale(fallback.code);
  }
}, { immediate: true });

function showToast(
	message: string,
	type: "error" | "info" = "error",
	duration = 5000,
) {
	if (toastTimer) clearTimeout(toastTimer);
	toast.value = { message, type };
	toastTimer = setTimeout(dismissToast, duration);
}

function focusPlayerName() {
	const el = document.getElementById("player-name") as HTMLInputElement | null;
	if (el) el.focus();
}

function onRoomCodeComplete(val: string) {
	// When code is filled, auto-join if the player name exists; otherwise focus Join.
	nextTick(() => {
		if (playerName.value.trim()) {
			if (!isCheckingRoom.value) void joinRoom();
		} else {
			if (joinBtnRef.value) joinBtnRef.value.focus();
		}
	});
}

function onRoomCodeSubmit() {
	// Enter pressed inside the code inputs: if name present, join; otherwise focus name.
	if (playerName.value.trim()) {
		void joinRoom();
	} else {
		focusPlayerName();
	}
}

function onNameEnter() {
	// If a room code has been entered, Enter should join that room; otherwise create.
  if (roomCodeModel.value?.trim()) {
		void joinRoom();
	} else {
		void createRoom();
	}
}

function dismissToast() {
	if (toastTimer) clearTimeout(toastTimer);
	toast.value = null;
}

async function createRoom() {
	if (!playerName.value.trim()) {
		showToast("Please enter your name");
		return;
	}

	try {
		const resp = await fetch(`${API_HOST}/api/rooms`, { method: "POST" });
		if (!resp.ok) {
			showToast("Failed to create room. Please try again.");
			return;
		}
		const data = await resp.json();
		const roomCode = data.room_code;

		const playerId = getOrCreatePlayerId();
		store.setLocalPlayer(playerId, playerName.value.trim());
		store.setRoomCode(roomCode);

		connect(roomCode);
		router.push({ name: "room", params: { roomCode } });
	} catch (err) {
		console.error("Error creating room:", err);
		showToast("Failed to create room. Please try again.");
	}
}

async function joinRoom() {
	if (!playerName.value.trim()) {
		showToast("Please enter your name");
		return;
	}
	// should only allow 6 character room codes that are alphanumeric

	if (!roomCodeModel.value) {
		showToast("Please enter a room code");
		return;
	}

	// Normalize and validate room code using shared helpers
	const code = normalizeRoomCode(roomCodeModel.value);

	if (!isValidRoomCode(code)) {
		showToast("Room code must be 6 characters (A–Z, 0–9)");
		return;
	}

	isCheckingRoom.value = true;

	try {
		const response = await fetch(`${API_HOST}/api/rooms/${code}/status`);
		const data = await response.json();

		if (!data.exists) {
			showToast(
				`That room doesn't exist. Join a different room or create a new one!`,
				"error",
			);
			return;
		}
	} catch {
		// Status check failed — proceed and let the WS connection handle it
	} finally {
		isCheckingRoom.value = false;
	}

	const playerId = getOrCreatePlayerId();
	store.setLocalPlayerAndSave(playerId, playerName.value.trim());
	store.setRoomCodeAndSave(code);

	connect(code);
	router.push({ name: "room", params: { roomCode: code } });
}

async function joinRandomRoom() {
	if (!playerName.value.trim()) {
		showToast("Please enter your name");
		return;
	}

	dismissToast();
	isJoiningRandom.value = true;

	try {
		const response = await fetch(`${API_HOST}/api/rooms/random`);

		if (!response.ok) {
			showToast(
				response.status === 404
					? "No available rooms found. Try creating a new room!"
					: "Failed to find a room. Please try again.",
			);
			return;
		}

		const data = await response.json();
		const roomCode = data.room_code;

		const playerId = getOrCreatePlayerId();
		store.setLocalPlayerAndSave(playerId, playerName.value.trim());
		store.setRoomCodeAndSave(roomCode);

		connect(roomCode);
		router.push({ name: "room", params: { roomCode } });
	} catch (err) {
		console.error("Error joining random room:", err);
		showToast("Failed to connect. Please try again.");
	} finally {
		isJoiningRandom.value = false;
	}
}
</script>

<template>
  <div class="screen">
    <Transition name="toast">
      <div v-if="toast" :class="['toast', `toast--${toast.type}`]" role="alert" aria-live="assertive">
        <span class="toast-message">{{ toast.message }}</span>
        <button type="button" class="toast-close" aria-label="Dismiss" @click="dismissToast">×</button>
      </div>
    </Transition>

    <div class="container">
      <h1>🎨 {{ $t('home.title') }}</h1>
      <p class="subtitle">{{ $t('home.subtitle') }}</p>

      <div class="lobby-layout">
        <div class="card">
          <h2>{{ $t('home.createOrJoin') }}</h2>

          <div class="input-group">
            <label for="player-name">{{ $t('home.yourName') }}</label>
            <input
              id="player-name"
              v-model="playerName"
              type="text"
              :placeholder="$t('home.enterYourName')"
              maxlength="20"
              @keyup.enter="onNameEnter"
            >
          </div>

          <LocaleSelector id="player-locale" v-model="playerLocale" :options="localeOptions" label="Language" compact />

          <div class="button-group">
            <button type="button" class="btn btn-create" @click="createRoom">{{ $t('home.createRoom') }}</button>

            <div class="divider"><span>{{ $t('home.orJoin') }}</span></div>

            <div class="join-room-group">
              <RoomCodeInput v-model="roomCodeModel" @complete="onRoomCodeComplete" @submit="onRoomCodeSubmit" />
              <button ref="joinBtnRef" type="button" class="btn btn-join" :disabled="isCheckingRoom" @click="joinRoom">
                {{ isCheckingRoom ? $t('home.checking') : $t('home.joinRoom') }}
              </button>
            </div>

            <div class="divider"><span>{{ $t('home.or') }}</span></div>

            <button type="button" class="btn btn-random" :disabled="isJoiningRandom" @click="joinRandomRoom">
              {{ isJoiningRandom ? $t('home.findingRoom') : $t('home.joinRandomRoom') }}
            </button>
          </div>
        </div>

        <div class="how-to-play-card">
          <button
            type="button"
            class="how-to-play-toggle"
            :aria-expanded="howToPlayOpen"
            @click="howToPlayOpen = !howToPlayOpen"
          >
            <span>{{ $t('home.howToPlay') }}</span>
            <svg
              class="toggle-chevron"
              :class="{ open: howToPlayOpen }"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              aria-hidden="true"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          <Transition name="collapse">
            <div v-if="howToPlayOpen" class="how-to-play-body">
              <ol class="steps-list">
                <li>
                  <span class="step-num">1</span>
                  <span>{{ $t('home.step1', { count: 10 }) }}</span>
                </li>
                <li>
                  <span class="step-num">2</span>
                  <span>{{ $t('home.step2', { time: 60 }) }}</span>
                </li>
                <li>
                  <span class="step-num">3</span>
                  <span>{{ $t('home.step3') }}</span>
                </li>
                <li>
                  <span class="step-num">4</span>
                  <span>{{ $t('home.step4') }}</span>
                </li>
              </ol>
            </div>
          </Transition>
        </div>
      </div>

      <footer class="site-footer">
        <p>
          A multiplayer web version of
          <a href="https://gamelygames.com/products/six-second-scribbles" target="_blank" rel="noopener"
            >Six Second Scribbles</a
          >
          by Gamely Games · Inspired by
          <a href="https://github.com/OliverCulleyDeLange/6ss" target="_blank" rel="noopener"
            >Oliver Culley de Lange's solo version</a
          >
          ·
          <a href="https://github.com/simonvanlierde/6-second-scribbles" target="_blank" rel="noopener"
            >Source on GitHub</a
          >
        </p>
      </footer>
    </div>
  </div>
</template>

<style scoped>
</style>

<style scoped>
/* ── Toast ─────────────────────────────────────────────── */
.toast {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1.25rem;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.18);
  font-size: 0.9375rem;
  font-weight: 500;
  max-width: min(90vw, 480px);
  width: max-content;
}

.toast--error {
  background: #1a1a2e;
  color: #fff;
  border-left: 4px solid #e74c3c;
}

.toast--info {
  background: #1a1a2e;
  color: #fff;
  border-left: 4px solid var(--color-primary);
}

.toast-message {
  flex: 1;
  line-height: 1.4;
}

.toast-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
}

.toast-btn {
  padding: 0.35rem 0.85rem;
  border-radius: 6px;
  border: none;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.toast-btn--confirm {
  background: #f6c90e;
  color: #1a1a2e;
}

.toast-btn--confirm:hover {
  background: #e5b800;
}

.toast-btn--dismiss {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.toast-btn--dismiss:hover {
  background: rgba(255, 255, 255, 0.2);
}

.toast-close {
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.6);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
  flex-shrink: 0;
}

.toast-close:hover {
  color: #fff;
}

.missing-room-dialog {
  border: 0;
  border-radius: 20px;
  padding: 0;
  background: rgba(10, 12, 28, 0.95);
  color: white;
  box-shadow: 0 30px 90px rgba(0, 0, 0, 0.4);
  width: min(92vw, 420px);
}

.missing-room-dialog::backdrop {
  background: rgba(0, 0, 0, 0.55);
}

.missing-room-form {
  padding: 1.5rem;
  display: grid;
  gap: 0.75rem;
}

.missing-room-form h2,
.missing-room-form p {
  margin: 0;
}

.missing-room-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(12px);
}

/* ── Layout ────────────────────────────────────────────── */
.lobby-layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ── Buttons ───────────────────────────────────────────── */
.btn-create {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 700;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.btn-create:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.45);
}

.btn-join {
  background: var(--color-success);
  color: white;
  font-weight: 600;
  width: 100%;
  margin-top: 0.75rem;
  transition:
    background 0.2s ease,
    transform 0.2s ease;
}

.btn-join:hover:not(:disabled) {
  background: var(--color-success-dark);
  transform: translateY(-1px);
}

.btn-random {
  background: var(--color-primary);
  color: white;
  font-weight: 600;
  transition:
    background 0.2s ease,
    transform 0.2s ease;
}

.btn-random:hover:not(:disabled) {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
}

/* ── Divider ───────────────────────────────────────────── */
.divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #bbb;
  font-size: 0.8125rem;
}

.divider::before,
.divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: #eee;
}

/* ── Join room group ───────────────────────────────────── */
.join-room-group {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.locale-select {
  width: 100%;
}

/* ── How to Play ───────────────────────────────────────── */
.how-to-play-card {
  background: rgba(255, 255, 255, 0.92);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.how-to-play-toggle {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-dark);
}

.how-to-play-toggle:hover {
  background: rgba(0, 0, 0, 0.03);
}

.toggle-chevron {
  transition: transform 0.25s ease;
  color: var(--color-primary);
  flex-shrink: 0;
}

.toggle-chevron.open {
  transform: rotate(180deg);
}

.how-to-play-body {
  padding: 0.25rem 1.5rem 1.25rem;
}

.steps-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.steps-list li {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  font-size: 0.9375rem;
  color: #4a5568;
  line-height: 1.5;
}

.step-num {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.625rem;
  height: 1.625rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  font-size: 0.75rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

/* Collapse transition */
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

.collapse-enter-to,
.collapse-leave-from {
  max-height: 300px;
  opacity: 1;
}

/* ── Footer ────────────────────────────────────────────── */
.site-footer {
  margin-top: 1.5rem;
  text-align: center;
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.6;
  padding-bottom: 1rem;
}

.site-footer a {
  color: rgba(255, 255, 255, 0.85);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.site-footer a:hover {
  color: #fff;
}
</style>
