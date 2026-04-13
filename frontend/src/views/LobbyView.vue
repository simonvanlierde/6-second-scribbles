<script setup lang="ts">
import { useClipboard } from "@vueuse/core";
import { computed, ref } from "vue";
import { useRoute } from "vue-router";

import GameSettingsPanel from "@/components/GameSettingsPanel.vue";
import PlayerListPanel from "@/components/PlayerListPanel.vue";
import SharedDrawpad from "@/components/SharedDrawpad.vue";
import { useNotifications } from "@/composables/notifications";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { GAME_SETTINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const route = useRoute();
const store = useGameStore();
const { send } = useGameConnection();
const { showNotification } = useNotifications();
const { copy } = useClipboard();
const { leaveRoom } = useLeaveRoom();

const leaveDialogRef = ref<HTMLDialogElement | null>(null);

const localPadVisible = computed({
	get: () => store.localPadVisible,
	set: (v: boolean) => {
		store.setLocalPadVisible(v);
	},
});

const roomCode = computed(() => route.params.roomCode as string);
const playerCount = computed(() => store.playersList.length);
const canStart = computed(() => store.canStartGame && store.isHost);

function handleClear() {
	if (store.isHost) {
		store.clearStrokes();
		send({ type: "drawpad_clear" });
	}
}

function toggleDrawpad() {
	localPadVisible.value = !localPadVisible.value;
}

function startGame() {
	if (!canStart.value) return;

	send({
		type: "start_game",
		difficulty: store.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
		rounds: store.maxRounds || GAME_SETTINGS.rounds.DEFAULT,
		drawingTimeLimit:
			store.drawingTimeLimit || GAME_SETTINGS.drawingTimeLimitSeconds.DEFAULT,
		guessingTimeLimit:
			store.guessingTimeLimit || GAME_SETTINGS.guessingTimeLimitSeconds.DEFAULT,
	});
}

async function copyRoomCode() {
	await copy(roomCode.value);
	showNotification("Copied!");
}

function showLeaveDialog() {
	leaveDialogRef.value?.showModal();
}

function cancelLeave() {
	leaveDialogRef.value?.close();
}

function confirmLeave() {
	leaveDialogRef.value?.close();
	leaveRoom();
}

function toggleRoomPadVisibility() {
	const visible = !store.roomPadVisible;
	store.setRoomPadVisible(visible);
	send({ type: "pad_visibility", visible });
}
</script>

<template>
  <div class="screen">
    <div class="container">
      <!-- Header -->
      <div class="room-header">
        <button type="button" class="btn-leave" @click="showLeaveDialog">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="15 18 9 12 15 6" />
          </svg>
          {{ $t('lobby.leaveRoom') }}
        </button>

        <button type="button" class="room-code-btn" title="Click to copy room code" @click="copyRoomCode">
          🎨
          <span class="room-code-text">{{ roomCode }}</span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
            class="copy-icon"
          >
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
          </svg>
        </button>

      </div>

      <!-- Two-column layout -->
      <div class="waiting-room-grid">
        <!-- Left: Players + Settings + Start -->
        <div class="card main-panel">
          <h2>{{ $t('lobby.players', { count: playerCount }) }}</h2>
          <PlayerListPanel />

          <div class="settings-section"><GameSettingsPanel /></div>

          <div v-if="store.isHost" class="start-section">
            <button type="button" class="btn btn-start" :disabled="!canStart" @click="startGame">
              {{ canStart ? $t('lobby.startGame') : $t('lobby.waitingForPlayers') }}
            </button>
          </div>
          <p v-else class="waiting-message">
            {{ playerCount >= 2 ? $t('lobby.waitingForHost') : $t('lobby.waitingForMore') }}
          </p>
        </div>

        <!-- Right: Drawpad (hidden for non-hosts when host disabled it) -->
        <div v-if="store.isHost || store.roomPadVisible" class="drawpad-panel">
          <div class="drawpad-section">
            <div class="drawpad-top">
              <h3 class="drawpad-title">{{ $t('lobby.doodleTitle') }}</h3>
            </div>

            <!-- Host-only: controls that affect everyone -->
            <div v-if="store.isHost" class="drawpad-control-bar">
              <button type="button" class="ctrl-btn ctrl-btn--ghost ctrl-btn--compact" @click="handleClear">
                {{ $t('lobby.clearForAll') }}
              </button>
              <button type="button" class="ctrl-btn ctrl-btn--ghost ctrl-btn--compact" @click="toggleRoomPadVisibility">
                {{ store.roomPadVisible ? $t('lobby.hideForAll') : $t('lobby.showForAll') }}
              </button>
              <button
                v-if="store.roomPadVisible"
                type="button"
                class="ctrl-btn ctrl-btn--outline ctrl-btn--compact"
                @click="toggleDrawpad"
              >
                {{ localPadVisible ? $t('lobby.hideMyPad') : $t('lobby.showMyPad') }}
              </button>
            </div>
            <button v-else-if="!store.isHost" type="button" class="ctrl-btn ctrl-btn--outline" @click="toggleDrawpad">
              {{ localPadVisible ? $t('lobby.hideMyPad') : $t('lobby.showMyPad') }}
            </button>

            <div v-if="store.roomPadVisible && localPadVisible" class="drawpad-canvas"><SharedDrawpad /></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Leave confirmation dialog -->
    <dialog ref="leaveDialogRef" class="leave-dialog" @click.self="cancelLeave">
      <h2>{{ $t('lobby.leaveDialogTitle') }}</h2>
      <p>{{ $t('lobby.leaveDialogText') }}</p>
      <div class="dialog-actions">
        <button type="button" class="btn btn-outline-dark" @click="cancelLeave">{{ $t('lobby.cancel') }}</button>
        <button type="button" class="btn btn-danger" @click="confirmLeave">{{ $t('lobby.leave') }}</button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
/* Override global screen to not vertically center (content can be tall) */
.screen {
  align-items: flex-start;
  padding-top: 1.25rem;
}

/* ── Header ────────────────────────────────────────────── */
.room-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.btn-leave {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background: rgba(255, 255, 255, 0.12);
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  color: white;
  border-radius: var(--radius-md);
  padding: 0.5rem 0.875rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-leave:hover {
  background: rgba(255, 255, 255, 0.22);
  border-color: rgba(255, 255, 255, 0.75);
}

.room-code-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: rgba(255, 255, 255, 0.15);
  border: 1.5px solid rgba(255, 255, 255, 0.45);
  border-radius: var(--radius-md);
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.room-code-btn:hover {
  background: rgba(255, 255, 255, 0.28);
  border-color: white;
}

.room-code-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
  font-size: 1.2rem;
  font-weight: 700;
  color: white;
  letter-spacing: 0.12em;
}

.copy-icon {
  color: rgba(255, 255, 255, 0.7);
  flex-shrink: 0;
}

/* ── Grid layout ───────────────────────────────────────── */
.waiting-room-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 768px) {
  .waiting-room-grid {
    grid-template-columns: 1fr;
  }
}

/* ── Main panel ────────────────────────────────────────── */
.main-panel {
  /* inherits .card from global */
}

.settings-section {
  border-top: 1px solid #eee;
  padding-top: 0.5rem;
  margin-top: 0.5rem;
}

.start-section {
  margin-top: 1rem;
}

.btn-start {
  width: 100%;
  padding: 0.9rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 1.0625rem;
  font-weight: 700;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.btn-start:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(102, 126, 234, 0.4);
}

.btn-start:disabled {
  background: #c0c0c0;
  color: #666;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.waiting-message {
  margin-top: 1rem;
  padding: 0.875rem;
  text-align: center;
  color: #4a5568;
  font-weight: 500;
  background: #ebf4ff;
  border-radius: var(--radius-md);
  border: 1px solid #bee3f8;
  font-size: 0.9375rem;
}

/* ── Drawpad panel ─────────────────────────────────────── */
.drawpad-panel {
  /* sits in the right grid column */
}

.drawpad-section {
  background: white;
  border-radius: var(--radius-xl);
  padding: 1.25rem;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.drawpad-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.drawpad-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--color-text-dark);
  margin: 0;
}

.drawpad-control-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.ctrl-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.ctrl-btn {
  padding: 0.375rem 0.75rem;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.ctrl-btn--compact {
  padding: 0.3rem 0.65rem;
}

.ctrl-btn--ghost {
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.25);
  color: var(--color-primary-dark);
}

.ctrl-btn--ghost:hover {
  background: rgba(102, 126, 234, 0.18);
}

.ctrl-btn--outline {
  background: rgba(72, 187, 120, 0.1);
  border: 1px solid rgba(72, 187, 120, 0.3);
  color: var(--color-success-dark);
}

.ctrl-btn--outline:hover {
  background: rgba(72, 187, 120, 0.18);
}

.drawpad-canvas {
  margin-top: 0.25rem;
}

.drawpad-canvas :global(.mini-canvas) {
  height: 320px;
}

@media (max-width: 768px) {
  .drawpad-canvas :global(.mini-canvas) {
    height: 220px;
  }
}

/* ── Leave dialog ──────────────────────────────────────── */
.leave-dialog {
  border: none;
  border-radius: var(--radius-lg);
  padding: 2rem;
  max-width: 360px;
  width: calc(100% - 2rem);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  margin: 0;
}

.leave-dialog[open] {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.leave-dialog::backdrop {
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(2px);
}

.leave-dialog h2 {
  margin: 0 0 0.625rem;
  font-size: 1.25rem;
  color: var(--color-text-dark);
}

.leave-dialog p {
  margin: 0 0 1.5rem;
  color: var(--color-text-muted);
  font-size: 0.9375rem;
}

.dialog-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-outline-dark {
  background: none;
  border: 1.5px solid #cbd5e0;
  color: var(--color-text-dark);
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-outline-dark:hover {
  background: #f7fafc;
  border-color: #a0aec0;
}

.btn-danger {
  background: var(--color-danger);
  border: none;
  color: white;
  padding: 0.5rem 1.25rem;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-danger:hover {
  background: #c82333;
}
</style>
