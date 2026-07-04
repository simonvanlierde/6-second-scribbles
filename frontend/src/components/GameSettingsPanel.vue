<script setup lang="ts">
import { useTimeoutFn, watchDebounced } from "@vueuse/core";
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

import StepperInput from "@/components/StepperInput.vue";
import HdSegmented from "@/components/ui/HdSegmented.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import type { Difficulty } from "@/shared/types";
import { useGameStore } from "@/stores/game";

const { t } = useI18n();
const store = useGameStore();
const { send } = useGameConnection();
const { fetchLocaleAvailability, localeOptions } = useLocaleAvailability();

const difficulty = ref<Difficulty>(store.difficulty);
const rounds = ref<number>(store.maxRounds);
const drawingTimeLimit = ref<number>(store.drawingTimeLimit);
const guessingTimeLimit = ref<number>(store.guessingTimeLimit);
const settingsFlash = ref(false);
const advancedOpen = ref(false);

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];
const difficultyOptions = computed(() => DIFFICULTIES.map((d) => ({ value: d, label: t(`settings.${d}`) })));

void fetchLocaleAvailability();

const { start: startFlash } = useTimeoutFn(() => {
  settingsFlash.value = false;
}, UI_TIMINGS.SETTINGS_FLASH_MS);

function broadcastSettings() {
  if (store.isHost) {
    send({
      type: "settings_update",
      difficulty: difficulty.value,
      rounds: rounds.value,
      drawingTimeLimit: drawingTimeLimit.value,
      guessingTimeLimit: guessingTimeLimit.value,
    });
  }
}

// The room's content language follows the host automatically — no visible
// control. Prefer the host's own locale; fall back to the current room locale,
// then to any locale that actually has playable cards.
watch(
  [localeOptions, () => store.defaultLocale, () => store.localPlayerLocale, () => store.isHost],
  ([options]) => {
    if (!store.isHost || options.length === 0) return;
    const isEnabled = (code: string) => options.find((option) => option.code === code)?.enabled ?? false;
    const desired = isEnabled(store.localPlayerLocale)
      ? store.localPlayerLocale
      : isEnabled(store.defaultLocale)
        ? store.defaultLocale
        : options.find((option) => option.enabled)?.code;
    if (desired && desired !== store.defaultLocale) {
      send({ type: "default_locale_update", locale: desired });
    }
  },
  { immediate: true },
);

function setDifficulty(d: string) {
  difficulty.value = d as Difficulty;
}

// Push the host's local edits into the store so other screens (lobby, header,
// results) read them immediately. Guarded on isHost so an incoming
// settings_update doesn't round-trip store -> ref -> store; difficulty is
// included here too (it was previously the only setting that lagged the store
// until the server echoed it back).
watch([difficulty, rounds, drawingTimeLimit, guessingTimeLimit], ([d, r, dl, gl]) => {
  if (!store.isHost) return;
  store.difficulty = d;
  if (Number.isFinite(r)) store.maxRounds = r;
  if (Number.isFinite(dl)) store.drawingTimeLimit = dl;
  if (Number.isFinite(gl)) store.guessingTimeLimit = gl;
});

watchDebounced([difficulty, rounds, drawingTimeLimit, guessingTimeLimit], broadcastSettings, {
  debounce: 300,
});

watch(
  [() => store.difficulty, () => store.maxRounds, () => store.drawingTimeLimit, () => store.guessingTimeLimit],
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
  [() => store.difficulty, () => store.maxRounds, () => store.drawingTimeLimit, () => store.guessingTimeLimit],
  () => {
    settingsFlash.value = true;
    startFlash();
  },
);
</script>

<template>
  <!-- Non-host: read-only settings chips -->
  <div v-if="!store.isHost" class="settings settings--readonly" :class="{ 'settings-flash': settingsFlash }">
    <div class="settings-chips">
      <span class="chip chip--accent">{{ $t(`settings.${difficulty}`) }}</span>
      <span class="chip">{{ rounds }} {{ $t("settings.rounds") }}</span>
      <span class="chip">
        <svg
          class="label-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
        </svg>
        {{ drawingTimeLimit }}s
      </span>
      <span class="chip">
        <svg
          class="label-icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path
            d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"
          />
        </svg>
        {{ guessingTimeLimit }}s
      </span>
    </div>
  </div>

  <!-- Host: editable settings -->
  <div v-else class="settings">
    <!-- Difficulty + rounds sit side by side, stacking when space is tight -->
    <div class="settings__row">
      <div class="field">
        <label class="field__label">{{ $t("settings.difficulty") }}</label>
        <HdSegmented
          :model-value="difficulty"
          :options="difficultyOptions"
          :aria-label="$t('settings.difficulty')"
          @update:model-value="setDifficulty"
        />
      </div>

      <div class="field">
        <label class="field__label">{{ $t("settings.rounds") }}</label>
        <StepperInput
          v-model="rounds"
          :label="$t('settings.rounds')"
          :min="GAME_SETTINGS.rounds.MIN"
          :max="GAME_SETTINGS.rounds.MAX"
        />
      </div>
    </div>

    <!-- Advanced settings -->
    <button type="button" class="advanced-toggle" :aria-expanded="advancedOpen" @click="advancedOpen = !advancedOpen">
      <svg
        :class="{ 'is-open': advancedOpen }"
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
      {{ $t("settings.advancedSettings") }}
    </button>

    <Transition name="collapse">
      <div v-if="advancedOpen" class="advanced">
        <div class="advanced__times">
          <div class="field">
            <label class="field__label">
              <svg
                class="label-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path d="M12 20h9" />
                <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
              </svg>
              {{ $t("settings.drawingTime") }}
            </label>
            <StepperInput
              v-model="drawingTimeLimit"
              :label="$t('settings.drawingTime')"
              :min="GAME_SETTINGS.drawingTimeLimitSeconds.MIN"
              :max="GAME_SETTINGS.drawingTimeLimitSeconds.MAX"
              :step="10"
              suffix="s"
            />
          </div>

          <div class="field">
            <label class="field__label">
              <svg
                class="label-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                aria-hidden="true"
              >
                <path
                  d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"
                />
              </svg>
              {{ $t("settings.guessingTime") }}
            </label>
            <StepperInput
              v-model="guessingTimeLimit"
              :label="$t('settings.guessingTime')"
              :min="GAME_SETTINGS.guessingTimeLimitSeconds.MIN"
              :max="GAME_SETTINGS.guessingTimeLimitSeconds.MAX"
              :step="10"
              suffix=""
            />
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin: var(--space-4) 0;
}
.settings--readonly {
  padding: var(--space-3) var(--space-4);
  border: 1.5px dashed var(--color-ink);
  border-radius: var(--r-card);
}
.settings__row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-4);
  align-items: start;
}

.settings-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  font-family: var(--font-body);
  font-size: var(--text-label-sm);
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-pill);
  background: var(--color-card);
  color: var(--color-ink);
  box-shadow: var(--shadow-pill);
  text-transform: capitalize;
}
.chip--accent {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}

.field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
}
.field__label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--text-label-md);
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-ink-muted);
}
.label-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.advanced-toggle {
  display: inline-flex;
  align-self: flex-start;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  border: 0;
  background: transparent;
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  font-weight: 600;
  color: var(--color-marker-red);
  cursor: pointer;
}
.advanced-toggle svg {
  transition: transform var(--motion-base) var(--ease-out);
}
.advanced-toggle svg.is-open {
  transform: rotate(180deg);
}
.advanced {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-3);
  border: 1.5px dashed var(--color-ink);
  border-radius: var(--r-card);
}
.advanced__times {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--space-3);
}

.settings-flash {
  animation: flash-bg 0.9s ease-in-out;
}
@keyframes flash-bg {
  0% {
    background-color: color-mix(in srgb, var(--color-highlighter-yellow) 40%, transparent);
  }
  50% {
    background-color: color-mix(in srgb, var(--color-highlighter-yellow) 80%, transparent);
  }
  100% {
    background-color: transparent;
  }
}
@media (prefers-reduced-motion: reduce) {
  .settings-flash {
    animation: none;
  }
}
.collapse-enter-active,
.collapse-leave-active {
  transition: all var(--motion-base) var(--ease-out);
  overflow: hidden;
}
.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}
.collapse-enter-to,
.collapse-leave-from {
  max-height: 600px;
  opacity: 1;
}
</style>
