<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import { initGameEngine } from '@/composables/gameEngineInstance'
import { useLeaveRoom } from '@/composables/useLeaveRoom'
import { GAME_SETTINGS } from '@/config/gameConfig'
import type { Difficulty } from '@/shared/types'
import SharedDrawpad from '@/components/SharedDrawpad.vue'
import { useNotifications } from '@/composables/notifications'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import logger from '@/utils/logger'

const route = useRoute()
const router = useRouter()
const store = useGameStore()
const { send } = useGameConnection()
const { leave: leaveRoom } = useLeaveRoom()

// Ensure we request the latest game/room state when this view mounts so the
// shared drawpad strokes (persisted server-side) are available immediately
// even if the user hasn't opened the drawpad yet.
onMounted(() => {
  try {
    send({ type: 'request_game_state', playerId: store.localPlayerId })
  } catch (err) {
    // send is a no-op if the socket isn't open yet; ignore errors here
    // Log at debug level so developers can inspect failures when DEBUG=true
    logger.debug('[WaitingRoom] request_game_state send failed', err)
  }
})

const difficulty = ref<Difficulty>(GAME_SETTINGS.difficulty.DEFAULT)
const rounds = ref<number>(GAME_SETTINGS.rounds.DEFAULT)
const roundLength = ref<number>(GAME_SETTINGS.roundLengthSeconds.DEFAULT)
const showLeaveWarning = ref(false)
const roundsError = ref<string | null>(null)
// Persisted per-user in the store
const showDrawpad = computed({
  get: () => store.showDrawpad,
  set: (v: boolean) => store.setShowDrawpad(v),
})
const settingsFlash = ref(false)
let settingsBroadcastTimeout: number | null = null

const roomCode = computed(() => route.params.roomCode as string)
const playerCount = computed(() => store.playersList.length)
const canStart = computed(() => store.canStartGame && store.isHost)
// No inline tooltip anymore; rely on global toasts for copy feedback

function broadcastSettings() {
  // Debounce settings broadcast (300ms) for better performance
  if (settingsBroadcastTimeout) {
    clearTimeout(settingsBroadcastTimeout)
  }

  settingsBroadcastTimeout = window.setTimeout(() => {
    if (store.isHost) {
      send({
        type: 'settings_update',
        difficulty: difficulty.value,
        rounds: rounds.value,
        roundLength: roundLength.value,
      })
    }
  }, 300)
}

// Listen for clear command: host triggers a clear message; SharedDrawpad will
// react to store changes / server messages and clear its local canvas.

function toggleDrawpad() {
  const newVal = !showDrawpad.value
  showDrawpad.value = newVal
}

// SharedDrawpad handles incremental stroke sending, rendering, and clear events.

// Host-level drawpad controls (visibility and clear) state
const showClearConfirm = ref(false)
const { showNotification } = useNotifications()

function hostToggleRoomVisibility() {
  const newVal = !store.showPadForRoom
  store.setShowPadForRoom(newVal)
  send({ type: 'pad_visibility', playerId: store.localPlayerId, visible: newVal })
}

function promptClearForEveryone() {
  // open confirm dialog (we will not offer undo for shared clears)
  showClearConfirm.value = true
}

function doClearForEveryoneConfirmed() {
  // send clear and show a plain notification (no undo for shared clears)
  send({ type: 'drawpad_clear', playerId: store.localPlayerId })
  showClearConfirm.value = false
  showNotification('Shared pad cleared — this action cannot be undone')
}

function startGame() {
  if (!canStart.value) {
    logger.info('[UI] Cannot start game. canStart:', canStart.value)
    return
  }

  logger.info(
    '[UI] Starting game with difficulty:',
    difficulty.value,
    'Rounds:',
    rounds.value,
    'Round time:',
    roundLength.value
  )

  const start_game_message = {
    type: 'start_game' as const,
    difficulty: difficulty.value || GAME_SETTINGS.difficulty.DEFAULT,
    rounds: rounds.value || GAME_SETTINGS.rounds.DEFAULT,
    roundLength: roundLength.value || GAME_SETTINGS.roundLengthSeconds.DEFAULT,
  }
  logger.debug('[UI] Sending start_game message:', start_game_message)

  // Broadcast start_game message to all players
  send(start_game_message)

  // Host runs the game engine to coordinate the game
  if (store.isHost) {
    const gameEngine = initGameEngine()
    gameEngine.startGame(difficulty.value, rounds.value, roundLength.value)
  }
}

async function copyRoomCode() {
  try {
    await navigator.clipboard.writeText(roomCode.value)
    // Show a small toast notification
    const { showNotification } = useNotifications()
    showNotification('Copied!')
  } catch (err) {
    logger.error('Failed to copy room code:', err)
  }
}

function showLeaveConfirmation() {
  showLeaveWarning.value = true
}

function confirmLeave() {
  leaveRoom()
}

function adjustRoundLength(delta: number) {
  const newLength = roundLength.value + delta
  if (
    newLength >= GAME_SETTINGS.roundLengthSeconds.MIN &&
    newLength <= GAME_SETTINGS.roundLengthSeconds.MAX
  ) {
    roundLength.value = newLength
  }
}

function clampRounds() {
  if (rounds.value < GAME_SETTINGS.rounds.MIN) rounds.value = GAME_SETTINGS.rounds.MIN
  if (rounds.value > GAME_SETTINGS.rounds.MAX) rounds.value = GAME_SETTINGS.rounds.MAX
  rounds.value = Math.floor(rounds.value)
  // persist to store
  store.setMaxRounds(rounds.value)
}

// Inline validation as user types
watch(rounds, (val) => {
  if (!Number.isFinite(val)) {
    roundsError.value = 'Please enter a valid number'
    return
  }
  if (val < GAME_SETTINGS.rounds.MIN || val > GAME_SETTINGS.rounds.MAX) {
    roundsError.value = `Must be between ${GAME_SETTINGS.rounds.MIN} and ${GAME_SETTINGS.rounds.MAX}`
  } else {
    roundsError.value = null
    // persist valid value to store (store saves state)
    store.setMaxRounds(Math.floor(val))
    // Broadcast to other players if host
    if (store.isHost) {
      broadcastSettings()
    }
  }
})

// Update roundLength in store when it changes (server will persist)
watch(roundLength, (val) => {
  if (Number.isFinite(val)) {
    // store exposes roundLength ref; assign
    store.roundLength = val
    // Broadcast to other players if host (server will persist)
    if (store.isHost) {
      broadcastSettings()
    }
  }
})

// Watch difficulty changes: persist to store and broadcast if host
watch(difficulty, (val) => {
  // val should be a Difficulty string; persist to store
  if (typeof val === 'string') {
    store.setDifficulty(val as Difficulty)
  }
  if (store.isHost) {
    broadcastSettings()
  }
})

// Sync settings from store for non-hosts (when host changes them)
watch(
  () => store.difficulty,
  (val) => {
    if (!store.isHost) {
      difficulty.value = val
    }
  }
)

watch(
  () => store.maxRounds,
  (val) => {
    if (!store.isHost) {
      rounds.value = val
    }
  }
)

watch(
  () => store.roundLength,
  (val) => {
    if (!store.isHost) {
      roundLength.value = val
    }
  }
)

// Flash UI when host updates settings (non-hosts will see this)
watch([() => store.difficulty, () => store.maxRounds, () => store.roundLength], () => {
  settingsFlash.value = true
  setTimeout(() => (settingsFlash.value = false), 900)
})

// Canvas color/width controls are handled inside SharedDrawpad component.
</script>
<template>
  <div class="screen">
    <div class="container">
      <div class="header-with-back">
        <button class="btn btn-back" @click="showLeaveConfirmation">→🚪 Leave room</button>
        <h1>🎨 Room: {{ roomCode }}</h1>
      </div>

      <div class="card">
        <h2>Players ({{ playerCount }})</h2>
        <ul class="player-list">
          <li v-for="player in store.playersList" :key="player.id" class="player-item">
            <span class="player-name">{{ player.name }}</span>
            <span v-if="player.id === store.localPlayerId" class="player-badge">(You)</span>
            <span v-if="store.playersList[0]?.id === player.id" class="player-badge host"
              >Host</span
            >
          </li>
        </ul>

        <div v-if="store.isHost" class="game-settings">
          <div class="setting-group">
            <label for="difficulty-select">Difficulty:</label>
            <select id="difficulty-select" v-model="difficulty">
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>

          <div class="setting-group">
            <label for="rounds-input">Rounds:</label>
            <input
              id="rounds-input"
              type="number"
              v-model.number="rounds"
              :min="GAME_SETTINGS.rounds.MIN"
              :max="GAME_SETTINGS.rounds.MAX"
              step="1"
              @blur="clampRounds"
            />
            <small
              >Choose a number between {{ GAME_SETTINGS.rounds.MIN }} and
              {{ GAME_SETTINGS.rounds.MAX }}</small
            >
          </div>
          <!-- Advanced settings should take full width underneath other controls -->
          <details class="advanced-settings-fullwidth">
            <summary>Advanced Settings</summary>
            <div class="setting-group">
              <label for="round-time">Round Time (seconds):</label>
              <div class="round-time-controls">
                <button
                  class="btn btn-primary"
                  @click="adjustRoundLength(-10)"
                  :disabled="roundLength <= GAME_SETTINGS.roundLengthSeconds.MIN"
                >
                  -10s
                </button>
                <span>{{ roundLength }} seconds</span>
                <button
                  class="btn btn-primary"
                  @click="adjustRoundLength(10)"
                  :disabled="roundLength >= GAME_SETTINGS.roundLengthSeconds.MAX"
                >
                  +10s
                </button>
              </div>
            </div>
          </details>

          <div class="setting-group">
            <label></label>
            <div v-if="roundsError" class="input-error">{{ roundsError }}</div>
          </div>
        </div>

        <div v-if="store.isHost">
          <button class="btn btn-primary" :disabled="!canStart" @click="startGame">
            {{ canStart ? 'Start Game' : 'Waiting for players (need 2+)' }}
          </button>
        </div>

        <div v-else class="non-host-section">
          <div :class="['settings-preview-compact', { 'settings-flash': settingsFlash }]">
            <strong>Game Settings:</strong>
            <span class="setting-compact">{{ difficulty }}</span> •
            <span class="setting-compact">{{ rounds }} rounds</span> •
            <span class="setting-compact">{{ roundLength }}s per round</span>
          </div>
          <p class="waiting-message">
            {{
              playerCount >= 2
                ? 'Waiting for host to start the game...'
                : 'Waiting for more players to join...'
            }}
          </p>
        </div>

        <div class="share-room">
          <p>Share this room code with friends:</p>
          <div class="room-code-share" style="position: relative">
            <span class="room-code-display">{{ roomCode }}</span>
            <div style="display: inline-flex; align-items: center; gap: 0.5rem">
              <button class="btn btn-small" @click="copyRoomCode">Copy</button>
            </div>
          </div>
        </div>
        <!-- per-client toggle: always available when the room allows the pad (host can still hide for everyone from SharedDrawpad) -->
        <div class="share-drawpad-divider" />
        <div style="display: flex; justify-content: center; margin-top: 0.5rem; gap: 0.5rem">
          <!-- per-client toggle: only when the room allows the pad; toggles local visibility -->
          <button
            v-if="store.showPadForRoom"
            :class="['btn btn-small btn-personal']"
            @click="toggleDrawpad"
          >
            {{ showDrawpad ? (store.isHost ? 'Hide pad for me' : 'Hide pad') : 'Show pad' }}
          </button>
          <!-- Host-level controls: hide/show for everyone and clear -->
          <div v-if="store.isHost" style="display: flex; gap: 0.5rem; align-items: center">
            <button class="btn btn-small btn-host" @click="hostToggleRoomVisibility">
              {{ store.showPadForRoom ? 'Hide pad for everyone' : 'Show pad for everyone' }}
            </button>
            <button
              v-if="store.showPadForRoom"
              class="btn btn-small btn-host btn-danger"
              @click="promptClearForEveryone"
            >
              Clear pad for everyone
            </button>
          </div>
          <!-- host controls above handle both show/hide and clearing; no duplicate banner needed -->
        </div>

        <!-- divider between share code and drawpad -->
        <div class="share-drawpad-divider" />

        <div
          v-if="store.showPadForRoom && store.showDrawpad"
          class="drawpad-section"
          style="border-top: 1px solid #dee2e6; margin-top: 1.5rem; padding-top: 1.5rem"
        >
          <div class="drawpad-controls">
            <!-- SharedDrawpad will show host-only global controls; WaitingRoom only shows local toggle above -->
          </div>

          <div v-if="store.showDrawpad" class="drawpad-container">
            <!-- waiting room uses a slightly smaller logical canvas to avoid horizontal scrolling on smaller laptops -->
            <SharedDrawpad :logicalWidth="680" :logicalHeight="420" />
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-model="showLeaveWarning"
      title="Leave Room?"
      message="Are you sure you want to leave this room?"
      confirmText="Leave"
      cancelText="Cancel"
      @confirm="confirmLeave"
    />
    <ConfirmDialog
      v-model="showClearConfirm"
      title="Clear shared pad"
      message="This will clear the shared draw pad for everyone. This action cannot be undone. Continue?"
      confirmText="Clear"
      cancelText="Cancel"
      @confirm="doClearForEveryoneConfirmed"
    />
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

.player-list {
  list-style: none;
  padding: 0;
  margin: 1rem 0;
}

.player-item {
  padding: 0.75rem;
  margin: 0.5rem 0;
  background-color: #f8f9fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.player-name {
  font-weight: 500;
  flex: 1;
}

.player-badge {
  padding: 0.25rem 0.5rem;
  background-color: #e9ecef;
  border-radius: 3px;
  font-size: 0.875rem;
  color: #6c757d;
}

.player-badge.host {
  background-color: #ffc107;
  color: #000;
}

.game-settings {
  display: flex;
  gap: 1rem;
  margin: 1.5rem 0;
  flex-wrap: wrap;
  align-items: flex-start;
  align-content: flex-start;
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  flex: 1;
  min-width: 150px;
}

.setting-group label {
  font-weight: 500;
  font-size: 0.875rem;
}

.settings-flash {
  animation: flash-bg 0.9s ease-in-out;
}

@keyframes flash-bg {
  0% {
    background-color: rgba(102, 51, 153, 0.1);
  }
  50% {
    background-color: rgba(102, 51, 153, 0.25);
  }
  100% {
    background-color: transparent;
  }
}

.setting-group select,
.setting-group input {
  padding: 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 1rem;
}

.round-time-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.round-time-controls button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.round-time-controls button:disabled {
  background-color: #c0c0c0;
  cursor: not-allowed;
}

.btn[disabled],
.btn.btn-primary[disabled] {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #c0c0c0 !important;
  color: #666 !important;
}
.btn[disabled] {
  /* Room code near drawpad */
  .room-code-above {
    text-align: center;
    margin: 0.75rem 0;
    font-weight: 600;
  }
  .drawpad-container {
    position: relative;
  }
  .drawpad-controls .btn {
    margin-left: 0.5rem;
  }
  opacity: 0.6;
  cursor: not-allowed;
}

.input-error {
  color: #d9534f;
  font-size: 0.9rem;
  margin-top: 0.25rem;
}

.non-host-section {
  margin: 1.5rem 0;
}

.settings-preview-compact {
  padding: 0.75rem 1rem;
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
  font-size: 0.875rem;
  color: #495057;
}

.settings-preview-compact strong {
  color: #2c3e50;
  margin-right: 0.5rem;
}

.setting-compact {
  text-transform: capitalize;
  color: #2c3e50;
  font-weight: 500;
}

.waiting-message {
  padding: 1rem;
  text-align: center;
  color: #6c757d;
  font-weight: 500;
  background-color: #e7f3ff;
  border-radius: 4px;
}

.drawpad-section {
  margin: 2rem 0;
  padding: 1.5rem;
  background-color: #f8f9fa;
  border-radius: 8px;
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

.room-code-small {
  margin: 0;
  font-size: 0.875rem;
  color: #6c757d;
  font-family: monospace;
  font-weight: 600;
}

.drawpad-controls {
  display: flex;
  gap: 0.5rem;
}

.drawpad-container {
  margin-top: 1rem;
}

.canvas-tools {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background-color: white;
  border-radius: 4px;
  align-items: center;
}

.tool-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.tool-group label {
  font-weight: 500;
  font-size: 0.875rem;
  color: #495057;
}

.mini-canvas {
  width: 100%;
  max-width: 600px;
  height: 300px;
  border: 2px solid #dee2e6;
  border-radius: 4px;
  cursor: crosshair;
  background: white;
  display: block;
  margin: 0 auto;
}

.drawpad-hint {
  text-align: center;
  color: #6c757d;
  font-size: 0.875rem;
  margin-top: 0.5rem;
  font-style: italic;
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

/* Modal styles are provided by ConfirmDialog component */

.copy-tooltip {
  position: absolute;
  right: -4px;
  top: -32px;
  background: rgba(0, 0, 0, 0.85);
  color: #fff;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.85rem;
  white-space: nowrap;
  transform-origin: top right;
  animation: pop 220ms ease;
  z-index: 100;
}

/* Advanced settings should clear the flex flow and span full width below other controls */
.advanced-settings-fullwidth {
  width: 100%;
  display: block;
  margin-top: 0.75rem;
}
.advanced-settings-fullwidth .setting-group {
  width: 100%;
  min-width: 0;
}

/* Visual divider between share-room and drawpad */
.share-drawpad-divider {
  height: 1px;
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.06), rgba(0, 0, 0, 0.12));
  margin: 1rem 0 1.25rem 0;
  border-radius: 1px;
}

/* Host personal hide button - make it visually distinctive */

/* Host-level controls: yellow styling */
.btn-host {
  background: linear-gradient(180deg, #fff4cc, #ffe082);
  border: 1px solid #ffd54f;
  color: #5a3e00;
  font-weight: 600;
}

/* Personal hide/show button for individuals (gray) */
.btn-personal {
  background: linear-gradient(180deg, #f5f5f5, #e9e9e9);
  border: 1px solid #d0d0d0;
  color: #333;
}

@keyframes pop {
  from {
    transform: scale(0.85);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
