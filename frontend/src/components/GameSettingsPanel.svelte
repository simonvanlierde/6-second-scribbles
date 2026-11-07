<script lang="ts">
import { onDestroy, untrack } from "svelte";
import { slide } from "svelte/transition";
import StepperInput from "@/components/StepperInput.svelte";
import HdSegmented from "@/components/ui/HdSegmented.svelte";
import { useGameConnection } from "@/composables/useGameConnection.svelte";
import { useLocaleAvailability } from "@/composables/useLocaleAvailability.svelte";
import { GAME_SETTINGS, UI_TIMINGS } from "@/config/gameConfig";
import { t } from "@/i18n";
import type { Difficulty } from "@/shared/types";
import { useGameStore } from "@/stores/game.svelte";

const store = useGameStore();
const { send } = useGameConnection();
const availability = useLocaleAvailability();

let difficulty = $state<Difficulty>(store.difficulty);
let rounds = $state<number>(store.maxRounds);
let drawingTimeLimit = $state<number>(store.drawingTimeLimit);
let guessingTimeLimit = $state<number>(store.guessingTimeLimit);
let settingsFlash = $state(false);
let advancedOpen = $state(false);

const DIFFICULTIES: Difficulty[] = ["easy", "medium", "hard"];
let difficultyOptions = $derived.by(() => DIFFICULTIES.map((d) => ({ value: d, label: t(`settings.${d}`) })));

void availability.fetchLocaleAvailability();

let flashTimer: number | undefined;
function startFlash() {
  clearTimeout(flashTimer);
  flashTimer = window.setTimeout(() => {
    settingsFlash = false;
  }, UI_TIMINGS.SETTINGS_FLASH_MS);
}
onDestroy(() => {
  clearTimeout(flashTimer);
  clearTimeout(broadcastTimer);
});

function broadcastSettings() {
  if (store.isHost) {
    send({
      type: "settings_update",
      difficulty: difficulty,
      rounds: rounds,
      drawingTimeLimit: drawingTimeLimit,
      guessingTimeLimit: guessingTimeLimit,
    });
  }
}

// The room's content language follows the host automatically — no visible
// control. Prefer the host's own locale; fall back to the current room locale,
// then to any locale that actually has playable cards.
$effect(() => {
  const value = [availability.localeOptions, store.defaultLocale, store.localPlayerLocale, store.isHost] as const;
  untrack(() => {
    const [options] = value;
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
  });
});

function setDifficulty(d: string) {
  difficulty = d as Difficulty;
}

// Host edits update shared state immediately; received settings stay one-way for guests.
let watchStarted1 = false;
$effect(() => {
  const value = [difficulty, rounds, drawingTimeLimit, guessingTimeLimit] as const;
  if (!watchStarted1) {
    watchStarted1 = true;
    return;
  }
  untrack(() => {
    const [d, r, dl, gl] = value;
    if (!store.isHost) return;
    store.difficulty = d;
    if (Number.isFinite(r)) store.maxRounds = r;
    if (Number.isFinite(dl)) store.drawingTimeLimit = dl;
    if (Number.isFinite(gl)) store.guessingTimeLimit = gl;
  });
});

// Send once the host stops changing settings for 300 ms, not on every stepper click.
let broadcastTimer: number | undefined;
let watchStarted2 = false;
$effect(() => {
  const value = [difficulty, rounds, drawingTimeLimit, guessingTimeLimit] as const;
  if (!watchStarted2) {
    watchStarted2 = true;
    return;
  }
  untrack(() => {
    clearTimeout(broadcastTimer);
    broadcastTimer = window.setTimeout(broadcastSettings, 300);
  });
});

let watchStarted3 = false;
$effect(() => {
  const value = [store.difficulty, store.maxRounds, store.drawingTimeLimit, store.guessingTimeLimit] as const;
  if (!watchStarted3) {
    watchStarted3 = true;
    return;
  }
  untrack(() => {
    const [d, r, rl, gl] = value;
    if (!store.isHost) {
      difficulty = d;
      rounds = r;
      drawingTimeLimit = rl;
      guessingTimeLimit = gl;
    }
  });
});

let watchStarted4 = false;
$effect(() => {
  const value = [store.difficulty, store.maxRounds, store.drawingTimeLimit, store.guessingTimeLimit] as const;
  if (!watchStarted4) {
    watchStarted4 = true;
    return;
  }
  untrack(() => {
    settingsFlash = true;
    startFlash();
  });
});
</script>

<!-- Non-host: read-only settings chips -->
{#if !store.isHost}
  <div class={["settings settings--readonly", { "settings-flash": settingsFlash }]}>
    <div class="settings-chips">
      <span class="chip chip--accent">{t(`settings.${difficulty}`)}</span>
      <span class="chip">{rounds} {t("settings.rounds")}</span>
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
          <path d="M12 20h9"></path>
          <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
        </svg>
        {drawingTimeLimit}s
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
          ></path>
        </svg>
        {guessingTimeLimit}s
      </span>
    </div>
  </div>

  <!-- Host: editable settings -->
{:else}
  <div class="settings">
    <!-- Difficulty + rounds sit side by side, stacking when space is tight -->
    <div class="settings__row">
      <div class="field">
        <span class="field__label">{t("settings.difficulty")}</span>
        <HdSegmented
          modelValue={difficulty}
          options={difficultyOptions}
          ariaLabel={t("settings.difficulty")}
          onmodelValueChange={setDifficulty}
        ></HdSegmented>
      </div>

      <div class="field">
        <span class="field__label">{t("settings.rounds")}</span>
        <StepperInput
          bind:modelValue={rounds}
          label={t("settings.rounds")}
          min={GAME_SETTINGS.rounds.MIN}
          max={GAME_SETTINGS.rounds.MAX}
        ></StepperInput>
      </div>
    </div>

    <!-- Advanced settings -->
    <button
      class="advanced-toggle"
      type="button"
      aria-expanded={advancedOpen}
      onclick={() => {
        advancedOpen = !advancedOpen;
      }}
    >
      <svg
        class={[{ "is-open": advancedOpen }]}
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
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
      {t("settings.advancedSettings")}
    </button>

    {#if advancedOpen}
      <div
        class="advanced"
        transition:slide={{ duration: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 220 }}
      >
        <div class="advanced__times">
          <div class="field">
            <span class="field__label">
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
                <path d="M12 20h9"></path>
                <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
              </svg>
              {t("settings.drawingTime")}
            </span>
            <StepperInput
              bind:modelValue={drawingTimeLimit}
              label={t("settings.drawingTime")}
              min={GAME_SETTINGS.drawingTimeLimitSeconds.MIN}
              max={GAME_SETTINGS.drawingTimeLimitSeconds.MAX}
              step={10}
              suffix="s"
            ></StepperInput>
          </div>

          <div class="field">
            <span class="field__label">
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
                ></path>
              </svg>
              {t("settings.guessingTime")}
            </span>
            <StepperInput
              bind:modelValue={guessingTimeLimit}
              label={t("settings.guessingTime")}
              min={GAME_SETTINGS.guessingTimeLimitSeconds.MIN}
              max={GAME_SETTINGS.guessingTimeLimitSeconds.MAX}
              step={10}
              suffix=""
            ></StepperInput>
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}
<style>
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
  min-height: 44px;
  padding: 4px 0;
  border: 0;
  background: transparent;
  font-family: var(--font-body);
  font-size: var(--text-label-md);
  font-weight: 600;
  color: var(--color-primary-text);
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
</style>
