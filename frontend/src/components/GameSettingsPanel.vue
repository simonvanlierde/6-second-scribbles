<script setup lang="ts">
import { useTimeoutFn, watchDebounced } from "@vueuse/core";
import { computed, ref, watch } from "vue";
import LocaleSelector from "@/components/LocaleSelector.vue";
import StepperInput from "@/components/StepperInput.vue";
import { useGameConnection } from "@/composables/useGameConnection";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import { i18n } from "@/i18n";
import { formatLocaleLabel } from "@/shared/locales";
import type { Difficulty } from "@/shared/types";
import { useGameStore } from "@/stores/game";

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
    if (!store.isHost) return;
    const selected = options.find((option) => option.code === store.defaultLocale);
    if (selected?.enabled) return;
    const fallback = options.find((option) => option.enabled);
    if (fallback) changeDefaultLocale(fallback.code);
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

watch(rounds, (val) => {
  if (!Number.isFinite(val)) {
    roundsError.value = i18n.global.t("settings.enterValidNumber");
    return;
  }
  if (val < GAME_SETTINGS.rounds.MIN || val > GAME_SETTINGS.rounds.MAX) {
    roundsError.value = i18n.global.t("settings.mustBeBetween", {
      min: GAME_SETTINGS.rounds.MIN,
      max: GAME_SETTINGS.rounds.MAX,
    });
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

const difficultyChipClass: Record<Difficulty, string> = {
  easy: "border-green-500 text-green-800 bg-green-50",
  medium: "border-primary text-primary-dark bg-indigo-50",
  hard: "border-red-500 text-red-700 bg-red-50",
};
</script>

<template>
  <!-- Non-host: read-only settings chips -->
  <div
    v-if="!store.isHost"
    class="my-4 rounded-md border border-slate-200 bg-surface px-4 py-3.5"
    :class="{ 'settings-flash': settingsFlash }"
  >
    <div class="flex flex-wrap items-center gap-2">
      <span
        class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[0.8125rem] font-medium text-ink-dark capitalize"
      >
        {{ `🌐 ${formatLocaleLabel(store.defaultLocale)}` }}
      </span>
      <span
        class="rounded-full border px-2.5 py-1 text-[0.8125rem] font-medium capitalize"
        :class="difficultyChipClass[difficulty]"
      >
        {{ $t(`settings.${difficulty}`) }}
      </span>
      <span
        class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[0.8125rem] font-medium text-ink-dark capitalize"
      >
        {{ rounds }}
        {{ $t("settings.rounds") }}
      </span>
      <span
        class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[0.8125rem] font-medium text-ink-dark capitalize"
      >
        ✏️ {{ drawingTimeLimit }}s
      </span>
      <span
        class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[0.8125rem] font-medium text-ink-dark capitalize"
      >
        💬 {{ guessingTimeLimit }}s
      </span>
    </div>
  </div>

  <!-- Host: editable settings -->
  <div v-else class="my-4 flex flex-col gap-4">
    <!-- Language -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[0.8125rem] font-semibold tracking-wider text-ink-muted uppercase">
        🌐 {{ $t("settings.roomLanguage") }}
      </label>
      <LocaleSelector
        id="room-default-locale"
        :model-value="store.defaultLocale"
        :options="localeOptions"
        compact
        @update:model-value="changeDefaultLocale"
      />
      <p class="m-0 text-[0.8125rem] leading-snug text-ink-muted">{{ $t("settings.fallbackHelp") }}</p>
    </div>

    <!-- Difficulty -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[0.8125rem] font-semibold tracking-wider text-ink-muted uppercase">
        {{ $t("settings.difficulty") }}
      </label>
      <div class="flex gap-1.5" role="group" :aria-label="$t('settings.difficulty')">
        <button
          v-for="d in DIFFICULTIES"
          :key="d"
          type="button"
          class="flex-1 cursor-pointer rounded-full border-[1.5px] border-slate-200 bg-white px-2 py-1.5 text-sm font-medium text-[#555] capitalize transition-all"
          :class="
            difficulty === d
              ? '!border-transparent !font-semibold !text-white bg-gradient-to-br !from-primary !to-secondary'
              : 'hover:border-primary hover:text-primary'
          "
          @click="setDifficulty(d)"
        >
          {{ $t(`settings.${d}`) }}
        </button>
      </div>
    </div>

    <!-- Rounds -->
    <div class="flex flex-col gap-1.5">
      <label class="text-[0.8125rem] font-semibold tracking-wider text-ink-muted uppercase">
        {{ $t("settings.rounds") }}
      </label>
      <StepperInput
        v-model="rounds"
        :label="$t('settings.rounds')"
        :min="GAME_SETTINGS.rounds.MIN"
        :max="GAME_SETTINGS.rounds.MAX"
      />
      <p v-if="roundsError" class="mt-0.5 text-[0.8125rem] text-danger">{{ roundsError }}</p>
    </div>

    <!-- Advanced settings -->
    <button
      type="button"
      class="flex cursor-pointer items-center gap-1.5 border-0 bg-transparent py-1 text-sm font-semibold text-primary"
      :aria-expanded="advancedOpen"
      @click="advancedOpen = !advancedOpen"
    >
      <svg
        class="transition-transform duration-200"
        :class="{ 'rotate-180': advancedOpen }"
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
      <div v-if="advancedOpen" class="flex flex-col gap-3.5 rounded-md border border-slate-200 bg-surface p-3.5">
        <div class="flex flex-col gap-1.5">
          <label class="text-[0.8125rem] font-semibold tracking-wider text-ink-muted uppercase">
            ✏️ {{ $t("settings.drawingTime") }}
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

        <div class="flex flex-col gap-1.5">
          <label class="text-[0.8125rem] font-semibold tracking-wider text-ink-muted uppercase">
            💬 {{ $t("settings.guessingTime") }}
          </label>
          <StepperInput
            v-model="guessingTimeLimit"
            :label="$t('settings.guessingTime')"
            :min="GAME_SETTINGS.guessingTimeLimitSeconds.MIN"
            :max="GAME_SETTINGS.guessingTimeLimitSeconds.MAX"
            :step="10"
            suffix="s"
          />
        </div>
      </div>
    </Transition>

    <!-- Private room toggle -->
    <div class="pt-1">
      <label class="flex cursor-pointer items-start gap-3">
        <span class="relative mt-0.5 flex-shrink-0">
          <input
            v-model="isPrivateRoom"
            type="checkbox"
            class="peer absolute h-0 w-0 opacity-0"
            @change="togglePrivacy"
          >
          <span
            class="block h-5 w-10 rounded-full bg-slate-300 transition-colors peer-checked:bg-primary relative after:absolute after:top-[0.2rem] after:left-[0.2rem] after:h-4 after:w-4 after:rounded-full after:bg-white after:shadow-[0_1px_3px_rgba(0,0,0,0.2)] after:transition-transform peer-checked:after:translate-x-[1.1rem]"
            aria-hidden="true"
          />
        </span>
        <span class="flex flex-col gap-0.5 text-[0.9375rem] font-medium text-ink-dark">
          {{ $t("settings.privateRoom") }}
          <span class="text-xs font-normal text-ink-muted"> {{ $t("settings.privateRoomHelp") }} </span>
        </span>
      </label>
    </div>
  </div>
</template>

<style scoped>
.settings-flash {
  animation: flash-bg 0.9s ease-in-out;
}
@keyframes flash-bg {
  0% {
    background-color: rgba(102, 51, 153, 0.08);
  }
  50% {
    background-color: rgba(102, 51, 153, 0.18);
  }
  100% {
    background-color: transparent;
  }
}
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
</style>
