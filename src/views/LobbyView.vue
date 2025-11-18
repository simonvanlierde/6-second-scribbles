<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import RoomCodeInput from '@/components/RoomCodeInput.vue'
import { generateRoomCode as sharedGenerateRoomCode } from '@/shared/roomCode'

const router = useRouter()
const store = useGameStore()
const { connect } = useGameConnection()

const playerName = ref(store.localPlayerName) // Pre-fill with stored name

const roomCodeModel = ref('')

function onCodeComplete(_code: string) {
  // placeholder for accessibility announcements or auto-join hook
}
const error = ref('')

// Use shared generator directly

function generatePlayerId(): string {
  return `player_${Date.now()}_${Math.random().toString(36).substring(7)}`
}

function getOrCreatePlayerId(): string {
  // Try to get existing player ID from localStorage to avoid ghost players on reload
  const existingId = localStorage.getItem('player_id')
  if (existingId) {
    return existingId
  }

  // Generate new ID and store it
  const newId = generatePlayerId()
  localStorage.setItem('player_id', newId)
  return newId
}

function createRoom() {
  if (!playerName.value.trim()) {
    error.value = 'Please enter your name'
    return
  }

  const roomCode = sharedGenerateRoomCode()
  const playerId = getOrCreatePlayerId()

  store.setLocalPlayer(playerId, playerName.value.trim()) // Updated to use setLocalPlayer
  store.setRoomCode(roomCode)
  // Don't pre-add player - let the server message handlers do it

  connect(roomCode)
  router.push(`/room/${roomCode}`)
}

function joinRoom() {
  if (!playerName.value.trim()) {
    error.value = 'Please enter your name'
    return
  }

  if (!roomCodeModel.value) {
    error.value = 'Please enter a room code'
    return
  }

  const code = roomCodeModel.value
  const playerId = getOrCreatePlayerId()

  store.setLocalPlayerAndSave(playerId, playerName.value.trim())
  store.setRoomCodeAndSave(code)
  // Don't pre-add player - let the server message handlers do it

  connect(code)
  router.push(`/room/${code}`)
}

async function joinRandomRoom() {
  if (!playerName.value.trim()) {
    error.value = 'Please enter your name'
    return
  }

  error.value = ''

  try {
    const BACKEND_HOST = (import.meta as any).env?.VITE_BACKEND_HOST || 'http://localhost:8000'
    const response = await fetch(`${BACKEND_HOST}/api/rooms/random`)

    if (!response.ok) {
      if (response.status === 404) {
        error.value = 'No available rooms found. Try creating a new room!'
      } else {
        error.value = 'Failed to find a room. Please try again.'
      }
      return
    }

    const data = await response.json()
    const roomCode = data.room_code

    const playerId = getOrCreatePlayerId()
    store.setLocalPlayerAndSave(playerId, playerName.value.trim())
    store.setRoomCodeAndSave(roomCode)

    connect(roomCode)
    router.push(`/room/${roomCode}`)
  } catch (err) {
    console.error('Error joining random room:', err)
    error.value = 'Failed to connect. Please try again.'
  }
}
</script>

<template>
  <div class="screen">
    <div class="container">
      <h1>🎨 Six Second Scribbles</h1>
      <p class="subtitle">Multiplayer Drawing Party Game</p>

      <div class="lobby-content">
        <div class="card">
          <h2>Create or Join a Room</h2>

          <div v-if="error" class="error-message" role="alert" aria-live="assertive">
            {{ error }}
          </div>

          <div class="input-group">
            <label for="player-name">Your Name</label>
            <input
              id="player-name"
              v-model="playerName"
              type="text"
              placeholder="Enter your name"
              maxlength="20"
              @keyup.enter="createRoom"
            />
          </div>

          <div class="button-group">
            <button class="btn btn-primary" @click="createRoom">Create Room</button>
            <div class="divider">or</div>
            <button class="btn btn-random" @click="joinRandomRoom">🎲 Join Random Room</button>
            <div class="divider">or</div>
            <div class="input-group">
              <RoomCodeInput v-model="roomCodeModel" @complete="onCodeComplete" />
              <div style="display: flex; justify-content: center; margin-top: 0.75rem">
                <button class="btn btn-secondary" @click="joinRoom">Join Room</button>
              </div>
            </div>
          </div>
        </div>

        <div class="info-card">
          <h3>How to Play</h3>
          <ol>
            <li>Each player gets a different category with 10 items to draw</li>
            <li>Draw as many items as you can in 60 seconds</li>
            <li>Then guess what other players drew</li>
            <li>Both drawer and guesser get points for correct guesses!</li>
          </ol>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.error-message {
  color: #e74c3c;
  padding: 0.5rem;
  margin-bottom: 1rem;
  border: 1px solid #e74c3c;
  border-radius: 4px;
  background-color: #fadbd8;
}

/* Room code inputs */
.room-code-inputs {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  align-items: center;
  margin-top: 0.5rem;
}
.room-code-inputs .code-input {
  width: 2.25rem;
  height: 2.75rem;
  text-align: center;
  font-size: 1.25rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  outline: none;
}
.room-code-inputs .code-input:focus {
  border-color: #5b8def;
  box-shadow: 0 0 0 3px rgba(91, 141, 239, 0.12);
}

.btn-random {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn-random:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
</style>
