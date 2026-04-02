<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute } from "vue-router";

import GameSettingsPanel from "@/components/GameSettingsPanel.vue";
import PlayerListPanel from "@/components/PlayerListPanel.vue";
import SharedDrawpad from "@/components/SharedDrawpad.vue";
import { injectGameEngine } from "@/composables/injectionKeys";
import { useNotifications } from "@/composables/notifications";
import { useGameConnection } from "@/composables/useGameConnection";
import { useGameEngine } from "@/composables/useGameEngine";
import { useLeaveRoom } from "@/composables/useLeaveRoom";
import { GAME_SETTINGS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

const route = useRoute();
const store = useGameStore();
const { send } = useGameConnection();
const { showNotification } = useNotifications();
const gameEngineRef = injectGameEngine();
const { leaveRoom } = useLeaveRoom(gameEngineRef);

const leaveDialogRef = ref<HTMLDialogElement | null>(null);
const showCopyTooltip = ref(false);

const showDrawpad = computed({
  get: () => store.showDrawpad,
  set: (v: boolean) => store.setShowDrawpad(v),
});

const roomCode = computed(() => route.params.roomCode as string);
const playerCount = computed(() => store.playersList.length);
const canStart = computed(() => store.canStartGame && store.isHost);

function handleClear() {
  if (store.isHost) {
    store.clearStrokes();
    send({ type: "drawpad_clear", playerId: store.localPlayerId });
  }
}

function toggleDrawpad() {
  const newVal = !showDrawpad.value;
  showDrawpad.value = newVal;
  if (store.isHost) {
    send({ type: "pad_visibility", playerId: store.localPlayerId, visible: newVal });
  }
}

function startGame() {
  if (!canStart.value) return;

  send({
    type: "start_game",
    difficulty: store.difficulty || GAME_SETTINGS.difficulty.DEFAULT,
    rounds: store.maxRounds || GAME_SETTINGS.rounds.DEFAULT,
    roundLength: store.roundLength || GAME_SETTINGS.roundLengthSeconds.DEFAULT,
  });

  if (store.isHost) {
    gameEngineRef.value = useGameEngine();
    gameEngineRef.value.startGame(store.difficulty, store.maxRounds, store.roundLength);
  }
}

async function copyRoomCode() {
  try {
    await navigator.clipboard.writeText(roomCode.value);
    showNotification("Copied!");
    showCopyTooltip.value = true;
    setTimeout(() => (showCopyTooltip.value = false), 800);
  } catch {
    // clipboard not available
  }
}

function showLeaveConfirmation() {
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
  store.setShowPadForRoom(!store.showPadForRoom);
  send({ type: "pad_visibility", playerId: store.localPlayerId, visible: store.showPadForRoom });
}
</script>

<template>
  <div class="screen">
    <div class="container">
      <div class="header-with-back">
        <button type="button" class="btn btn-secondary btn-back" @click="showLeaveConfirmation">← Back</button>
        <h1>🎨 Room: {{ roomCode }}</h1>
      </div>

      <div class="card">
        <h2>Players ({{ playerCount }})</h2>
        <PlayerListPanel />

        <GameSettingsPanel />

        <!-- Host start button -->
        <div v-if="store.isHost">
          <button type="button" class="btn btn-primary" :disabled="!canStart" @click="startGame">
            {{ canStart ? 'Start Game' : 'Waiting for players (need 2+)' }}
          </button>
        </div>

        <!-- Non-host waiting message -->
        <p v-else class="waiting-message">
          {{ playerCount >= 2 ? 'Waiting for host to start the game...' : 'Waiting for more players to join...' }}
        </p>

        <!-- Shared drawpad -->
        <div class="drawpad-section">
          <div class="drawpad-header">
            <div class="drawpad-title">
              <h3>🎨 Doodle While You Wait!</h3>
            </div>
            <div class="drawpad-controls">
              <button v-if="store.isHost" type="button" class="btn btn-small" @click="handleClear">
                Clear drawpad for everyone
              </button>
              <button v-if="store.isHost" type="button" class="btn btn-small" @click="toggleRoomPadVisibility">
                {{ store.showPadForRoom ? 'Hide drawpad for everyone' : 'Show drawpad for everyone' }}
              </button>
              <button type="button" class="btn btn-small" @click="toggleDrawpad">
                {{ showDrawpad ? 'Hide pad' : 'Show pad' }}
              </button>
            </div>
          </div>

          <div v-if="store.showPadForRoom && store.showDrawpad" class="drawpad-container"><SharedDrawpad /></div>
        </div>

        <div class="share-room">
          <p>Share this room code with friends:</p>
          <div class="room-code-share">
            <span class="room-code-display">{{ roomCode }}</span>
            <div style="display: inline-flex; align-items: center; gap: 0.5rem">
              <button type="button" class="btn btn-small" @click="copyRoomCode">Copy</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Leave confirmation modal (native <dialog> for built-in focus trap, ESC, aria-modal) -->
    <dialog ref="leaveDialogRef" class="leave-dialog" @click.self="cancelLeave">
      <h2>Leave Room?</h2>
      <p>Are you sure you want to leave this room?</p>
      <div class="modal-actions">
        <button type="button" class="btn btn-secondary" @click="cancelLeave">Cancel</button>
        <button type="button" class="btn btn-danger" @click="confirmLeave">Leave</button>
      </div>
    </dialog>
  </div>
</template>

<style scoped>
.header-with-back {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.btn-back {
  flex-shrink: 0;
}

.header-with-back h1 {
  margin: 0;
  flex: 1;
  text-align: center;
}

.waiting-message {
  padding: 1rem;
  text-align: center;
  color: #6c757d;
  font-weight: 500;
  background-color: #e7f3ff;
  border-radius: 4px;
  margin: 1rem 0;
}

.drawpad-section {
  margin: 2rem 0;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: var(--radius-md);
  border: 1px solid #dee2e6;
}

.drawpad-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.drawpad-title {
  flex: 1;
}

.drawpad-title h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  color: #2c3e50;
}

.drawpad-controls {
  display: flex;
  gap: 0.5rem;
}

.drawpad-container {
  margin-top: 1rem;
}

.share-room {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #dee2e6;
}

.share-room p {
  margin-bottom: 0.75rem;
  color: #6c757d;
  font-size: 0.875rem;
}

.room-code-share {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.room-code-display {
  flex: 1;
  padding: 0.75rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  font-family: monospace;
  font-size: 1.25rem;
  font-weight: bold;
  text-align: center;
  letter-spacing: 0.1em;
}

.leave-dialog {
  border: none;
  border-radius: var(--radius-md);
  padding: 2rem;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.leave-dialog::backdrop {
  background-color: rgba(0, 0, 0, 0.5);
}

.leave-dialog h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--color-text);
}

.leave-dialog p {
  margin-bottom: 1.5rem;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-danger {
  background-color: var(--color-danger);
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

.btn[disabled],
.btn.btn-primary[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #c0c0c0;
  color: #666;
}
</style>
