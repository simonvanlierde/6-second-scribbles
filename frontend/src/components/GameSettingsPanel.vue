<script setup lang="ts">
import { useTimeoutFn, watchDebounced } from "@vueuse/core";
import { computed, ref, watch } from "vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import type { Difficulty } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const store = useGameStore();
const { send } = useGameConnection();

const difficulty = ref<Difficulty>(store.difficulty);
const rounds = ref<number>(store.maxRounds);
const roundLength = ref<number>(store.roundLength);
const roundsError = ref<string | null>(null);
const settingsFlash = ref(false);
const isPrivateRoom = computed({
  get: () => store.isPrivateRoom,
  set: (value: boolean) => store.setPrivacy(value),
});

const { start: startFlash } = useTimeoutFn(() => {
  settingsFlash.value = false;
}, UI_TIMINGS.SETTINGS_FLASH_MS);

function broadcastSettings() {
  if (store.isHost && !roundsError.value) {
    send({
      type: "settings_update",
      difficulty: difficulty.value,
      rounds: rounds.value,
      roundLength: roundLength.value,
    });
  }
}

function changeLanguage(newLanguage: string) {
  if (store.isHost) {
    send({ type: "language_update", language: newLanguage });
  }
}

function togglePrivacy() {
  if (store.isHost) {
    send({ type: "privacy_changed", isPrivate: isPrivateRoom.value });
  }
}

function adjustRoundLength(delta: number) {
  const newLength = roundLength.value + delta;
  if (newLength >= GAME_SETTINGS.roundLengthSeconds.MIN && newLength <= GAME_SETTINGS.roundLengthSeconds.MAX) {
    roundLength.value = newLength;
  }
}

function clampRounds() {
  if (rounds.value < GAME_SETTINGS.rounds.MIN) rounds.value = GAME_SETTINGS.rounds.MIN;
  if (rounds.value > GAME_SETTINGS.rounds.MAX) rounds.value = GAME_SETTINGS.rounds.MAX;
  rounds.value = Math.floor(rounds.value);
  store.maxRounds = rounds.value;
}

// Host: validate rounds on change
watch(rounds, (val) => {
  if (!Number.isFinite(val)) {
    roundsError.value = "Please enter a valid number";
    return;
  }
  if (val < GAME_SETTINGS.rounds.MIN || val > GAME_SETTINGS.rounds.MAX) {
    roundsError.value = `Must be between ${GAME_SETTINGS.rounds.MIN} and ${GAME_SETTINGS.rounds.MAX}`;
  } else {
    roundsError.value = null;
    store.maxRounds = Math.floor(val);
  }
});

watch(roundLength, (val) => {
  if (Number.isFinite(val)) store.roundLength = val;
});

// Host: debounced broadcast whenever any setting changes (auto-cleaned on unmount)
watchDebounced([difficulty, rounds, roundLength], broadcastSettings, { debounce: 300 });

// Non-host: sync all settings from store in one watcher
watch([() => store.difficulty, () => store.maxRounds, () => store.roundLength], ([d, r, rl]) => {
  if (!store.isHost) {
    difficulty.value = d;
    rounds.value = r;
    roundLength.value = rl;
  }
});

// Flash settings when they change (visible to all players)
watch([() => store.difficulty, () => store.maxRounds, () => store.roundLength], () => {
  settingsFlash.value = true;
  startFlash();
});
</script>

<template>
  <!-- Non-host: read-only settings preview -->
  <div v-if="!store.isHost" class="non-host-section">
    <div :class="['settings-preview-compact', { 'settings-flash': settingsFlash }]">
      <strong>Game Settings:</strong>
      <span class="setting-compact">{{ difficulty }}</span>
      •
      <span class="setting-compact">{{ rounds }} rounds</span>
      •
      <span class="setting-compact">{{ roundLength }}s per round</span>
    </div>
  </div>

  <!-- Host: editable settings form -->
  <div v-else class="game-settings">
    <div class="setting-group">
      <label for="language-select">🌐 Language:</label>
      <select
        id="language-select"
        :value="store.language"
        @change="changeLanguage(($event.target as HTMLSelectElement).value)"
      >
        <option value="en">English</option>
        <option value="es">Español</option>
        <option value="fr">Français</option>
      </select>
    </div>

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
        v-model.number="rounds"
        type="number"
        :min="GAME_SETTINGS.rounds.MIN"
        :max="GAME_SETTINGS.rounds.MAX"
        step="1"
        @blur="clampRounds"
      >
      <small>Choose a number between {{ GAME_SETTINGS.rounds.MIN }} and {{ GAME_SETTINGS.rounds.MAX }}</small>
    </div>

    <details>
      <summary>Advanced Settings</summary>
      <div class="setting-group">
        <label for="round-time">Round Time (seconds):</label>
        <div class="round-time-controls">
          <button
            type="button"
            class="btn btn-primary"
            :disabled="roundLength <= GAME_SETTINGS.roundLengthSeconds.MIN"
            @click="adjustRoundLength(-10)"
          >
            -10s
          </button>
          <span>{{ roundLength }} seconds</span>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="roundLength >= GAME_SETTINGS.roundLengthSeconds.MAX"
            @click="adjustRoundLength(10)"
          >
            +10s
          </button>
        </div>
      </div>
    </details>

    <div class="setting-group">
      <label>
        <input v-model="isPrivateRoom" type="checkbox" @change="togglePrivacy">
        Private Room
        <small class="privacy-hint">Private rooms won't appear in random room join</small>
      </label>
    </div>

    <div v-if="roundsError" class="input-error">{{ roundsError }}</div>
  </div>
</template>

<style scoped>
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

.privacy-hint {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #6c757d;
  font-style: italic;
}

.setting-group label input[type="checkbox"] {
  margin-right: 0.5rem;
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
</style>
