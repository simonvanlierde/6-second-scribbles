<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import { initGameEngine, clearGameEngine } from '@/composables/gameEngineInstance'
import { GAME_SETTINGS } from '@/config/gameConfig'
import type { Difficulty } from '@/shared/types'
import SharedDrawpad from '@/components/SharedDrawpad.vue'
import { useNotifications } from '@/composables/notifications'

const route = useRoute()
const router = useRouter()
const store = useGameStore()
const { send, disconnect } = useGameConnection()

const difficulty = ref<Difficulty>(GAME_SETTINGS.difficulty.DEFAULT)
const rounds = ref<number>(GAME_SETTINGS.rounds.DEFAULT)
const roundLength = ref<number>(GAME_SETTINGS.roundLengthSeconds.DEFAULT)
const showLeaveWarning = ref(false)
const roundsError = ref<string | null>(null)
const showCopyTooltip = ref(false)
const isPrivateRoom = ref(false)
const activeKickVotes = ref<Map<string, { currentVotes: number; requiredVotes: number; expiresAt: number }>>(new Map())
const showKickConfirm = ref<string | null>(null) // player ID to confirm kicking

// Expose activeKickVotes and handlers globally so useGameConnection can update it
;(window as any).__kickVotesState = {
  votes: activeKickVotes,
  showNotification
}

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
function handleClear() {
  if (store.isHost) {
    send({ type: 'drawpad_clear', playerId: store.localPlayerId })
  }
}

function toggleDrawpad() {
  const newVal = !showDrawpad.value
  showDrawpad.value = newVal

  // If we are host, broadcast visibility change to everyone
  if (store.isHost) {
    send({ type: 'pad_visibility', playerId: store.localPlayerId, visible: newVal })
  }
}

function togglePrivacy() {
  // Only host can change privacy
  if (store.isHost) {
    send({
      type: 'privacy_changed',
      playerId: store.localPlayerId,
      isPrivate: isPrivateRoom.value
    })
    console.log('[UI] Room privacy changed to:', isPrivateRoom.value)
  }
}

function initiateKick(targetPlayerId: string) {
  showKickConfirm.value = targetPlayerId
}

function confirmKick(targetPlayerId: string) {
  send({
    type: 'initiate_kick',
    playerId: store.localPlayerId,
    targetPlayerId: targetPlayerId
  })
  showKickConfirm.value = null
}

function cancelKick() {
  showKickConfirm.value = null
}

function voteToKick(targetPlayerId: string) {
  send({
    type: 'cast_kick_vote',
    playerId: store.localPlayerId,
    targetPlayerId: targetPlayerId
  })
}

function canKickPlayer(playerId: string): boolean {
  // Can't kick yourself
  if (playerId === store.localPlayerId) return false

  // Host can kick anyone except themselves
  if (store.isHost) return true

  // Non-hosts can initiate votes to kick
  return true
}

// SharedDrawpad handles incremental stroke sending, rendering, and clear events.

function startGame() {
  if (!canStart.value) {
    console.log('[UI] Cannot start game. canStart:', canStart.value)
    return
  }

  console.log(
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
  console.log('[UI] Sending start_game message:', start_game_message)

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
    showCopyTooltip.value = true
    setTimeout(() => (showCopyTooltip.value = false), 800)
  } catch (err) {
    console.error('Failed to copy room code:', err)
  }
}

function showLeaveConfirmation() {
  showLeaveWarning.value = true
}

function cancelLeave() {
  showLeaveWarning.value = false
}

function confirmLeave() {
  disconnect()
  clearGameEngine()
  store.reset()
  router.push('/')
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

// Persist roundLength to store when it changes
watch(roundLength, (val) => {
  if (Number.isFinite(val)) {
    // store exposes roundLength ref; assign and save
    store.roundLength = val
    store.saveState()
    // Broadcast to other players if host
    if (store.isHost) {
      broadcastSettings()
    }
  }
})

// Watch difficulty changes and broadcast
watch(difficulty, () => {
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
        <button class="btn btn-secondary btn-back" @click="showLeaveConfirmation">← Back</button>
        <h1>🎨 Room: {{ roomCode }}</h1>
      </div>

      <div class="card">
        <h2>Players ({{ playerCount }})</h2>
        <ul class="player-list">
          <li v-for="player in store.playersList" :key="player.id" class="player-item">
            <div class="player-info">
              <span class="player-name">{{ player.name }}</span>
              <span v-if="player.id === store.localPlayerId" class="player-badge">(You)</span>
              <span v-if="store.playersList[0]?.id === player.id" class="player-badge host"
                >Host</span
              >
            </div>

            <!-- Kick vote status -->
            <div v-if="activeKickVotes.has(player.id)" class="kick-vote-status">
              <span class="vote-progress">
                Kick vote: {{ activeKickVotes.get(player.id)!.currentVotes }}/{{ activeKickVotes.get(player.id)!.requiredVotes }}
              </span>
              <button
                v-if="player.id !== store.localPlayerId"
                class="btn btn-small btn-vote"
                @click="voteToKick(player.id)"
              >
                Vote Kick
              </button>
            </div>

            <!-- Kick button -->
            <button
              v-if="canKickPlayer(player.id) && !activeKickVotes.has(player.id)"
              class="btn btn-small btn-kick"
              @click="initiateKick(player.id)"
            >
              {{ store.isHost && player.id !== store.hostId ? 'Kick' : 'Vote Kick' }}
            </button>
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

          <!-- Advanced settings for round time -->
          <details>
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

          <!-- Private Room Setting -->
          <div class="setting-group">
            <label>
              <input type="checkbox" v-model="isPrivateRoom" @change="togglePrivacy" />
              Private Room
              <small class="privacy-hint">Private rooms won't appear in random room join</small>
            </label>
          </div>

          <div class="setting-group">
            <label></label>
            <div v-if="roundsError" class="input-error">{{ roundsError }}</div>
          </div>
        </div>

        <!-- Host controls -->
        <div v-if="store.isHost">
          <button class="btn btn-primary" :disabled="!canStart" @click="startGame">
            {{ canStart ? 'Start Game' : 'Waiting for players (need 2+)' }}
          </button>
        </div>

        <!-- Non-host: Show read-only game settings and waiting message -->
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

        <!-- Shared Mini Drawpad -->
        <div class="drawpad-section">
          <div class="drawpad-header">
            <div class="drawpad-title">
              <h3>🎨 Doodle While You Wait!</h3>
            </div>
            <div class="drawpad-controls">
              <button v-if="store.isHost" class="btn btn-small" @click="handleClear">
                Clear drawpad for everyone
              </button>
              <button
                v-if="store.isHost"
                class="btn btn-small"
                @click="
                  () => {
                    store.setShowPadForRoom(!store.showPadForRoom)
                    send({
                      type: 'pad_visibility',
                      playerId: store.localPlayerId,
                      visible: store.showPadForRoom,
                    })
                  }
                "
              >
                {{
                  store.showPadForRoom ? 'Hide drawpad for everyone' : 'Show drawpad for everyone'
                }}
              </button>
              <!-- Local visibility toggle for this client -->
              <button class="btn btn-small" @click="toggleDrawpad">
                {{ showDrawpad ? 'Hide pad' : 'Show pad' }}
              </button>
            </div>
          </div>

          <div v-if="store.showPadForRoom && store.showDrawpad" class="drawpad-container">
            <SharedDrawpad />
          </div>
        </div>

        <div class="share-room">
          <p>Share this room code with friends:</p>
          <div class="room-code-share">
            <span class="room-code-display">{{ roomCode }}</span>
            <div style="display: inline-flex; align-items: center; gap: 0.5rem">
              <button class="btn btn-small" @click="copyRoomCode">Copy</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Leave confirmation modal -->
    <div v-if="showLeaveWarning" class="modal-overlay" @click="cancelLeave">
      <div class="modal-content" @click.stop>
        <h2>Leave Room?</h2>
        <p>Are you sure you want to leave this room?</p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="cancelLeave">Cancel</button>
          <button class="btn btn-danger" @click="confirmLeave">Leave</button>
        </div>
      </div>
    </div>

    <!-- Kick confirmation modal -->
    <div v-if="showKickConfirm" class="modal-overlay" @click="cancelKick">
      <div class="modal-content" @click.stop>
        <h2>{{ store.isHost ? 'Kick Player?' : 'Start Kick Vote?' }}</h2>
        <p v-if="store.isHost">
          Are you sure you want to kick {{ store.playersList.find(p => p.id === showKickConfirm)?.name }}?
        </p>
        <p v-else>
          Start a vote to kick {{ store.playersList.find(p => p.id === showKickConfirm)?.name }}?
          {{ store.playersList.find(p => p.id === showKickConfirm)?.id === store.hostId ? 'All players must vote unanimously to kick the host.' : 'Requires 2/3 majority vote.' }}
        </p>
        <div class="modal-actions">
          <button class="btn btn-secondary" @click="cancelKick">Cancel</button>
          <button class="btn btn-danger" @click="confirmKick(showKickConfirm!)">
            {{ store.isHost ? 'Kick' : 'Start Vote' }}
          </button>
        </div>
      </div>
    </div>
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
  justify-content: space-between;
  gap: 0.75rem;
}

.player-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
}

.player-name {
  font-weight: 500;
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

.btn-kick {
  background-color: #dc3545;
  color: white;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.btn-kick:hover {
  background-color: #c82333;
}

.btn-vote {
  background-color: #ff6b6b;
  color: white;
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.btn-vote:hover {
  background-color: #ff5252;
}

.kick-vote-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: #fff3cd;
  padding: 0.375rem 0.75rem;
  border-radius: 4px;
  border: 1px solid #ffc107;
}

.vote-progress {
  font-size: 0.875rem;
  font-weight: 600;
  color: #856404;
}

.game-settings {
  display: flex;
  gap: 1rem;
  margin: 1.5rem 0;
  flex-wrap: wrap;
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

.privacy-hint {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #6c757d;
  font-style: italic;
}

.setting-group label input[type='checkbox'] {
  margin-right: 0.5rem;
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

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.modal-content p {
  margin-bottom: 1.5rem;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}

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
