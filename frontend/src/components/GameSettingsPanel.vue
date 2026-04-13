<script setup lang="ts">
import LocaleSelector from "@/components/LocaleSelector.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import { formatLocaleLabel } from "@/shared/locales";
import type { Difficulty } from "@/shared/types";
import { useGameStore } from "@/stores/game";
import { useTimeoutFn, watchDebounced } from "@vueuse/core";
import { computed, ref, watch } from "vue";

const store = useGameStore();
const { send } = useGameConnection();
const { fetchLocaleAvailability, localeOptions } = useLocaleAvailability();

const difficulty = ref<Difficulty>(store.difficulty);
const rounds = ref<number>(store.maxRounds);
const drawingTimeLimit = ref<number>(store.drawingTimeLimit);
const guessingTimeLimit = ref<number>(store.guessingTimeLimit);
const roundsError = ref<string | null>(null);
const settingsFlash = ref(false);
const advancedOpen = ref(false);
const isPrivateRoom = computed({
	get: () => store.isPrivateRoom,
	set: (value: boolean) => store.setPrivacy(value),
});

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];

void fetchLocaleAvailability();

const { start: startFlash } = useTimeoutFn(() => {
	settingsFlash.value = false;
}, UI_TIMINGS.SETTINGS_FLASH_MS);

function broadcastSettings() {
	if (store.isHost && !roundsError.value) {
		send({
			type: "settings_update",
			difficulty: difficulty.value,
			rounds: rounds.value,
			drawingTimeLimit: drawingTimeLimit.value,
			guessingTimeLimit: guessingTimeLimit.value,
		});
	}
}

function changeDefaultLocale(newLocale: string) {
	if (store.isHost) {
		send({ type: "default_locale_update", locale: newLocale });
	}
}

watch(
	localeOptions,
	(options) => {
		if (!store.isHost) {
			return;
		}

		const selected = options.find(
			(option) => option.code === store.defaultLocale,
		);
		if (selected?.enabled) {
			return;
		}

		const fallback = options.find((option) => option.enabled);
		if (fallback) {
			changeDefaultLocale(fallback.code);
		}
	},
	{ immediate: true },
);

function togglePrivacy() {
	if (store.isHost) {
		send({ type: "privacy_changed", isPrivate: isPrivateRoom.value });
	}
}

function setDifficulty(d: Difficulty) {
	difficulty.value = d;
}

function adjustRounds(delta: number) {
	const next = rounds.value + delta;
	if (next >= GAME_SETTINGS.rounds.MIN && next <= GAME_SETTINGS.rounds.MAX) {
		rounds.value = next;
	}
}

function adjustRoundLength(delta: number) {
	const newLength = drawingTimeLimit.value + delta;
	if (
		newLength >= GAME_SETTINGS.drawingTimeLimitSeconds.MIN &&
		newLength <= GAME_SETTINGS.drawingTimeLimitSeconds.MAX
	) {
		drawingTimeLimit.value = newLength;
	}
}

function adjustGuessLength(delta: number) {
	const newLength = guessingTimeLimit.value + delta;
	if (
		newLength >= GAME_SETTINGS.guessingTimeLimitSeconds.MIN &&
		newLength <= GAME_SETTINGS.guessingTimeLimitSeconds.MAX
	) {
		guessingTimeLimit.value = newLength;
	}
}

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

watch(drawingTimeLimit, (val) => {
	if (Number.isFinite(val)) store.drawingTimeLimit = val;
});

watch(guessingTimeLimit, (val) => {
	if (Number.isFinite(val)) store.guessingTimeLimit = val;
});

watchDebounced(
	[difficulty, rounds, drawingTimeLimit, guessingTimeLimit],
	broadcastSettings,
	{ debounce: 300 },
);

watch(
	[
		() => store.difficulty,
		() => store.maxRounds,
		() => store.drawingTimeLimit,
		() => store.guessingTimeLimit,
	],
	([d, r, rl, gl]) => {
		if (!store.isHost) {
			difficulty.value = d;
			rounds.value = r;
			drawingTimeLimit.value = rl;
			guessingTimeLimit.value = gl;
		}
	},
);

watch(
	[
		() => store.difficulty,
		() => store.maxRounds,
		() => store.drawingTimeLimit,
		() => store.guessingTimeLimit,
	],
	() => {
		settingsFlash.value = true;
		startFlash();
	},
);
</script>

<template>
  <!-- Non-host: read-only settings chips -->
  <div v-if="!store.isHost" :class="['settings-preview', { 'settings-flash': settingsFlash }]">
    <div class="settings-chip-row">
      <span class="settings-chip">
        {{ `🌐 ${formatLocaleLabel(store.defaultLocale)}` }}
      </span>
      <span :class="['settings-chip', `diff-chip--${difficulty}`]">{{ difficulty }}</span>
      <span class="settings-chip">{{ rounds }} rounds</span>
      <span class="settings-chip">✏️ {{ drawingTimeLimit }}s</span>
      <span class="settings-chip">💬 {{ guessingTimeLimit }}s</span>
    </div>
  </div>

  <!-- Host: editable settings -->
  <div v-else class="settings-form">
    <!-- Language -->
    <div class="setting-item">
      <label class="setting-label">🌐 Room language</label>
      <LocaleSelector
        id="room-default-locale"
        :model-value="store.defaultLocale"
        :options="localeOptions"
        compact
        @update:model-value="changeDefaultLocale"
      />
      <p class="setting-help">Used as the shared fallback when a prompt or category is not available in a player's language.</p>
    </div>

    <!-- Difficulty -->
    <div class="setting-item">
      <label class="setting-label">Difficulty</label>
      <div class="pill-group" role="group" aria-label="Difficulty">
        <button
          v-for="d in DIFFICULTIES"
          :key="d"
          type="button"
          :class="['pill-btn', { active: difficulty === d }]"
          @click="setDifficulty(d)"
        >
          {{ d }}
        </button>
      </div>
    </div>

    <!-- Rounds -->
    <div class="setting-item">
      <label class="setting-label">Rounds</label>
      <div class="stepper" role="group" aria-label="Rounds">
        <button
          type="button"
          class="stepper-btn"
          :disabled="rounds <= GAME_SETTINGS.rounds.MIN"
          aria-label="Decrease rounds"
          @click="adjustRounds(-1)"
        >−</button>
        <span class="stepper-value">{{ rounds }}</span>
        <button
          type="button"
          class="stepper-btn"
          :disabled="rounds >= GAME_SETTINGS.rounds.MAX"
          aria-label="Increase rounds"
          @click="adjustRounds(1)"
        >+</button>
      </div>
      <p v-if="roundsError" class="input-error">{{ roundsError }}</p>
    </div>

    <!-- Advanced settings -->
    <button type="button" class="advanced-toggle" :aria-expanded="advancedOpen" @click="advancedOpen = !advancedOpen">
      <svg
        class="adv-chevron"
        :class="{ open: advancedOpen }"
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
        <polyline points="6 9 12 15 18 9" />
      </svg>
      Advanced Settings
    </button>

    <Transition name="collapse">
      <div v-if="advancedOpen" class="advanced-settings">
        <div class="setting-item">
          <label class="setting-label">✏️ Drawing time</label>
          <div class="stepper" role="group" aria-label="Drawing time">
            <button
              type="button"
              class="stepper-btn stepper-btn--wide"
              :disabled="drawingTimeLimit <= GAME_SETTINGS.drawingTimeLimitSeconds.MIN"
              @click="adjustRoundLength(-10)"
            >−10s</button>
            <span class="stepper-value">{{ drawingTimeLimit }}s</span>
            <button
              type="button"
              class="stepper-btn stepper-btn--wide"
              :disabled="drawingTimeLimit >= GAME_SETTINGS.drawingTimeLimitSeconds.MAX"
              @click="adjustRoundLength(10)"
            >+10s</button>
          </div>
        </div>

        <div class="setting-item">
          <label class="setting-label">💬 Guessing time</label>
          <div class="stepper" role="group" aria-label="Guessing time">
            <button
              type="button"
              class="stepper-btn stepper-btn--wide"
              :disabled="guessingTimeLimit <= GAME_SETTINGS.guessingTimeLimitSeconds.MIN"
              @click="adjustGuessLength(-10)"
            >−10s</button>
            <span class="stepper-value">{{ guessingTimeLimit }}s</span>
            <button
              type="button"
              class="stepper-btn stepper-btn--wide"
              :disabled="guessingTimeLimit >= GAME_SETTINGS.guessingTimeLimitSeconds.MAX"
              @click="adjustGuessLength(10)"
            >+10s</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Private room toggle -->
    <div class="setting-item setting-item--toggle">
      <label class="toggle-label">
        <span class="toggle-switch">
          <input v-model="isPrivateRoom" type="checkbox" class="toggle-input" @change="togglePrivacy">
          <span class="toggle-track" aria-hidden="true" />
        </span>
        <span class="toggle-text">
          Private Room
          <span class="setting-hint">Private rooms won't appear in random join</span>
        </span>
      </label>
    </div>
  </div>
</template>

<style scoped>
/* ── Non-host preview ──────────────────────────────────── */
.settings-preview {
  margin: 1rem 0;
  padding: 0.875rem 1rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid #e2e8f0;
}

.settings-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.settings-chip {
  padding: 0.3rem 0.7rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text-dark);
  text-transform: capitalize;
}

.diff-chip--easy   { border-color: #48bb78; color: #276749; background: #f0fff4; }
.diff-chip--medium { border-color: var(--color-primary); color: var(--color-primary-dark); background: #ebf0ff; }
.diff-chip--hard   { border-color: #e53e3e; color: #c53030; background: #fff5f5; }

.settings-flash {
  animation: flash-bg 0.9s ease-in-out;
}

@keyframes flash-bg {
  0%   { background-color: rgba(102, 51, 153, 0.08); }
  50%  { background-color: rgba(102, 51, 153, 0.18); }
  100% { background-color: transparent; }
}

/* ── Host form ─────────────────────────────────────────── */
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin: 1rem 0;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.setting-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.setting-help {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.4;
  color: var(--color-text-muted);
}

/* Language select */
.select-wrapper {
  position: relative;
}

.select-wrapper select {
  width: 100%;
  padding: 0.5rem 2rem 0.5rem 0.75rem;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-text-dark);
  background: white;
  appearance: none;
  cursor: pointer;
  transition: border-color 0.15s;
}

.select-wrapper::after {
  content: "▾";
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.select-wrapper select:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Difficulty pills */
.pill-group {
  display: flex;
  gap: 0.375rem;
}

.pill-btn {
  flex: 1;
  padding: 0.45rem 0.5rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 999px;
  background: white;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  text-transform: capitalize;
  color: #555;
  transition: all 0.15s;
}

.pill-btn:hover:not(.active) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.pill-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
  font-weight: 600;
}

/* Stepper */
.stepper {
  display: flex;
  align-items: stretch;
  border: 1.5px solid #e2e8f0;
  border-radius: var(--radius-md);
  overflow: hidden;
  max-width: 200px;
}

.stepper-btn {
  padding: 0.5rem 0.875rem;
  background: var(--color-surface);
  border: none;
  font-size: 1.125rem;
  font-weight: 700;
  cursor: pointer;
  color: var(--color-primary);
  transition: background 0.15s;
  line-height: 1;
}

.stepper-btn--wide {
  font-size: 0.8125rem;
  padding: 0.5rem 0.75rem;
}

.stepper-btn:hover:not(:disabled) {
  background: #e9ecef;
}

.stepper-btn:disabled {
  color: #ccc;
  cursor: not-allowed;
}

.stepper-value {
  flex: 1;
  text-align: center;
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-dark);
  padding: 0.5rem 0.25rem;
  border-left: 1.5px solid #e2e8f0;
  border-right: 1.5px solid #e2e8f0;
  min-width: 3rem;
}

/* Advanced toggle */
.advanced-toggle {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-primary);
  padding: 0.25rem 0;
}

.adv-chevron {
  transition: transform 0.2s ease;
}

.adv-chevron.open {
  transform: rotate(180deg);
}

.advanced-settings {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  padding: 0.875rem;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  border: 1px solid #e2e8f0;
}

/* Collapse transition */
.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.22s ease;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

.collapse-enter-to,
.collapse-leave-from {
  max-height: 400px;
  opacity: 1;
}

/* Private room toggle switch */
.setting-item--toggle {
  padding-top: 0.25rem;
}

.toggle-label {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  cursor: pointer;
}

.toggle-switch {
  position: relative;
  flex-shrink: 0;
  margin-top: 0.15rem;
}

.toggle-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-track {
  display: block;
  width: 2.5rem;
  height: 1.4rem;
  background: #cbd5e0;
  border-radius: 999px;
  position: relative;
  transition: background 0.2s;
}

.toggle-track::after {
  content: "";
  position: absolute;
  top: 0.2rem;
  left: 0.2rem;
  width: 1rem;
  height: 1rem;
  background: white;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.toggle-input:checked ~ .toggle-track {
  background: var(--color-primary);
}

.toggle-input:checked ~ .toggle-track::after {
  transform: translateX(1.1rem);
}

.toggle-text {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--color-text-dark);
}

.setting-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 400;
}

.input-error {
  color: var(--color-danger);
  font-size: 0.8125rem;
  margin-top: 0.1rem;
}
</style>
