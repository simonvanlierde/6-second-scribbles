<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'

import { useGameStore } from '@/stores/game'
import { useGameConnection } from '@/composables/useGameConnection'
import RoomCodeInput from '@/components/RoomCodeInput.vue'
import InlineAlert from '@/components/InlineAlert.vue'
import { generateRoomCode as sharedGenerateRoomCode } from '@/shared/roomCode'

const router = useRouter()
const store = useGameStore()
const { connect } = useGameConnection()

const playerName = ref(store.localPlayerName) // Pre-fill with stored name
const playerNameRef = ref<HTMLInputElement | null>(null)
const playerNameError = ref('')
const playerNameErrTimer = ref<number | null>(null)

function showFieldError(
  refVar: { value: string },
  msg: string,
  timerRef: Ref<number | null>,
  focusRef?: { value: HTMLInputElement | null }
) {
  refVar.value = msg
  if (timerRef.value) window.clearTimeout(timerRef.value)
  timerRef.value = window.setTimeout(() => {
    refVar.value = ''
    timerRef.value = null
  }, 3500)
  if (focusRef && focusRef.value) {
    focusRef.value.focus()
  }
}

const roomCodeModel = ref('')

const CODE_LEN = 6

const isJoinEnabled = computed(() => (roomCodeModel.value || '').length === CODE_LEN)

const joinBtnRef = ref<HTMLButtonElement | null>(null)

// hover / focus helper for the disabled Join button
const showJoinHelper = ref(false)
const showJoinHelperVisible = computed(
  () => showJoinHelper.value && !isJoinEnabled.value && !joinError.value
)

function setJoinHelper(visible: boolean) {
  // only allow showing helper when join is disabled
  if (!isJoinEnabled.value) showJoinHelper.value = visible
}

function onCodeComplete(code: string) {
  // set model and highlight join button (do NOT auto-join)
  roomCodeModel.value = code
  // focus the join button so Enter will activate it
  if (joinBtnRef.value) joinBtnRef.value.focus()
}

function onRoomInputEnter(_code: string) {
  // If join is enabled, trigger join action (simulate click)
  if (isJoinEnabled.value && joinBtnRef.value) {
    joinBtnRef.value.click()
  }
}

// inline temporary alerts next to the buttons (kept for server/action errors)
const createError = ref('')
const joinError = ref('')

// Use shared generator directly

function generatePlayerId(): string {
  // Prefer crypto.randomUUID when available for stable unique ids
  try {
    const g = globalThis as unknown as { crypto?: { randomUUID?: () => string } }
    if (g.crypto && typeof g.crypto.randomUUID === 'function') {
      return `player_${g.crypto.randomUUID()}`
    }
  } catch {
    /* ignore and fallback */
  }

  return `player_${Date.now()}_${Math.random().toString(36).substring(7)}`
}

function createRoom() {
  if (!playerName.value.trim()) {
    // show field-level helper and focus input
    showFieldError(playerNameError, 'Please enter your name', playerNameErrTimer, playerNameRef)
    return
  }

  const roomCode = sharedGenerateRoomCode()
  const playerId = generatePlayerId()

  store.setLocalPlayer(playerId, playerName.value.trim()) // Updated to use setLocalPlayer
  store.setRoomCode(roomCode)
  // Don't pre-add player - let the server message handlers do it

  connect(roomCode)
  router.push(`/room/${roomCode}`)
}

function joinRoom() {
  if (!playerName.value.trim()) {
    showFieldError(playerNameError, 'Please enter your name', playerNameErrTimer, playerNameRef)
    return
  }

  if (!roomCodeModel.value || roomCodeModel.value.length !== CODE_LEN) {
    // Room code missing - we rely on hover helper to prompt user to fill code.
    return
  }

  const code = roomCodeModel.value
  const playerId = generatePlayerId()

  store.setLocalPlayerAndSave(playerId, playerName.value.trim())
  store.setRoomCodeAndSave(code)
  // Don't pre-add player - let the server message handlers do it

  connect(code)
  router.push(`/room/${code}`)
}
</script>

<template>
  <div class="home-screen">
    <div class="home-container">
      <div class="home-header">
        <div class="logo-section">
          <h1 class="home-title">🎨 Six Second Scribbles</h1>
          <p class="home-subtitle">Multiplayer Drawing Party Game</p>
        </div>
      </div>

      <div class="home-content">
        <div class="card main-card">
          <h2 class="card-title">Create or Join a Room</h2>

          <div class="input-group">
            <label for="player-name" class="input-label">Your Name</label>
            <input
              id="player-name"
              ref="playerNameRef"
              v-model="playerName"
              :aria-describedby="playerNameError ? 'player-name-error' : undefined"
              type="text"
              class="text-input"
              placeholder="Enter your name"
              maxlength="20"
              @keyup.enter="createRoom"
            />
            <div
              v-if="playerNameError"
              id="player-name-error"
              class="input-error"
              aria-live="polite"
            >
              {{ playerNameError }}
            </div>
          </div>

          <div class="action-section">
            <div style="position: relative; display: inline-block">
              <button class="btn btn-primary btn-large" @click="createRoom">
                Create New Room
              </button>
              <InlineAlert v-model="createError" style="position: absolute; top: -2.25rem">{{
                createError
              }}</InlineAlert>
            </div>

            <div class="divider-section">
              <div class="divider-line"></div>
              <span class="divider-text">or</span>
              <div class="divider-line"></div>
            </div>

            <div class="join-section">
              <label class="input-label">Enter Room Code</label>
              <RoomCodeInput
                v-model="roomCodeModel"
                @complete="onCodeComplete"
                @enter="onRoomInputEnter"
              />
              <div style="display: flex; justify-content: center; margin-top: 1rem">
                <div
                  style="position: relative; display: inline-block"
                  @mouseenter="setJoinHelper(true)"
                  @mouseleave="setJoinHelper(false)"
                  @focusin="setJoinHelper(true)"
                  @focusout="setJoinHelper(false)"
                >
                  <button
                    ref="joinBtnRef"
                    class="btn btn-secondary btn-large"
                    :disabled="!isJoinEnabled"
                    :class="{ enabled: isJoinEnabled }"
                    @click="joinRoom"
                  >
                    Join Room
                  </button>
                  <InlineAlert v-model="joinError" style="position: absolute; top: -2.25rem">{{
                    joinError
                  }}</InlineAlert>
                  <div v-if="showJoinHelperVisible" class="join-hover-help">
                    Please enter a room code
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="info-card how-to-card">
          <div class="how-to-header">
            <h3>How to Play</h3>
            <p class="tagline">Fast rounds. Quick sketches. Big laughs.</p>
          </div>

          <ol class="how-steps">
            <li>
              <strong>Get a category.</strong>
              <div class="step-description">
                Each player receives a different category with a short list of items to draw.
              </div>
            </li>
            <li>
              <strong>Draw quickly.</strong>
              <div class="step-description">
                You have a short timer (default 60s) to sketch as many items as you can — simple
                shapes work best.
              </div>
            </li>
            <li>
              <strong>Guess the drawings.</strong>
              <div class="step-description">
                Switch to guessing mode and try to identify what others drew.
              </div>
            </li>
            <li>
              <strong>Score points.</strong>
              <div class="step-description">
                Both drawer and correct guessers earn points. Try to be clear and fast!
              </div>
            </li>
          </ol>

          <div class="credits-section">
            <div class="credits-divider"></div>
            <p class="credits-text">
              Inspired by
              <a
                href="https://gamelygames.com/products/six-second-scribbles"
                target="_blank"
                rel="noopener noreferrer"
                class="credits-link"
                >Six Second Scribbles</a
              >
              by Hazel Reynolds (Gamely Games). Web adaptation based on work by
              <a
                href="https://oliverdelange.co.uk/6ss/"
                target="_blank"
                rel="noopener noreferrer"
                class="credits-link"
                >Oliver Culley de Lange</a
              >.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-screen {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.home-container {
  max-width: 1200px;
  width: 100%;
}

.home-header {
  margin-bottom: 2rem;
}

.logo-section {
  text-align: center;
}

.home-title {
  font-size: clamp(2rem, 5vw, 3.5rem);
  color: white;
  margin: 0 0 0.5rem 0;
  text-shadow:
    0 2px 4px rgba(0, 0, 0, 0.2),
    0 4px 12px rgba(0, 0, 0, 0.15);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.home-subtitle {
  color: rgba(255, 255, 255, 0.95);
  font-size: clamp(1rem, 2.5vw, 1.25rem);
  margin: 0;
  font-weight: 500;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.home-content {
  display: grid;
  gap: 2rem;
}

.main-card {
  background: white;
  border-radius: 20px;
  padding: 2.5rem;
  box-shadow:
    0 10px 40px rgba(0, 0, 0, 0.15),
    0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 1.75rem;
  color: #2c3e50;
  margin: 0 0 2rem 0;
  text-align: center;
  font-weight: 700;
}

.input-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #4a5568;
  font-size: 0.95rem;
}

.text-input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 1rem;
  transition: all 0.2s;
  background: #f8fafc;
}

.text-input:hover {
  border-color: #cbd5e0;
  background: white;
}

.text-input:focus {
  outline: none;
  border-color: #667eea;
  background: white;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.action-section {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  margin-top: 2rem;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.1rem;
  border-radius: 12px;
  font-weight: 700;
  width: 100%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-large:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
}

.btn-large:active:not(:disabled) {
  transform: translateY(-1px);
}

.divider-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, #e2e8f0, transparent);
}

.divider-text {
  color: #a0aec0;
  font-size: 0.9rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.join-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.how-to-card {
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  padding: 2rem;
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.08),
    0 1px 3px rgba(0, 0, 0, 0.05);
}

.how-to-header {
  margin-bottom: 1.5rem;
}

.how-to-header h3 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  font-weight: 700;
}

.tagline {
  margin: 0;
  color: #718096;
  font-size: 1rem;
  font-style: italic;
}

.how-steps {
  padding-left: 1.5rem;
  margin: 0;
  list-style-position: outside;
}

.how-steps li {
  margin: 1.25rem 0;
  color: #2d3748;
  line-height: 1.6;
}

.how-steps li strong {
  color: #1a202c;
  font-size: 1.05rem;
}

.step-description {
  color: #718096;
  font-size: 0.95rem;
  margin-top: 0.375rem;
  line-height: 1.5;
}

.credits-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
}

.credits-divider {
  height: 1px;
  background: linear-gradient(to right, transparent, #e2e8f0, transparent);
  margin-bottom: 1rem;
}

.credits-text {
  font-size: 0.875rem;
  color: #718096;
  text-align: center;
  line-height: 1.6;
  margin: 0;
}

.credits-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.2s;
}

.credits-link:hover {
  color: #5568d3;
  text-decoration: underline;
}

@media (min-width: 768px) {
  .home-content {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }

  .main-card {
    padding: 3rem;
  }
}

@media (max-width: 480px) {
  .home-screen {
    padding: 1rem 0.75rem;
  }

  .main-card {
    padding: 1.5rem;
  }

  .how-to-card {
    padding: 1.5rem;
  }

  .btn-large {
    padding: 0.875rem 1.5rem;
    font-size: 1rem;
  }
}
</style>
