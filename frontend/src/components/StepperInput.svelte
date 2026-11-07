<script lang="ts">
import { untrack } from "svelte";
import { t } from "@/i18n";

let {
  label,
  min,
  max,
  step = 1,
  suffix = "",
  modelValue = $bindable(),
}: {
  label: string;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
} & { modelValue: number } = $props();

// Local editable string so invalid/in-progress text (letters, empty, out of
// range) can be shown to the user while we only push valid integers upward.
let raw = $state(String(modelValue));
let watchStarted0 = false;
$effect(() => {
  const value = modelValue;
  if (!watchStarted0) {
    watchStarted0 = true;
    return;
  }
  untrack(() => {
    const v = value;
    if (Number.parseInt(raw, 10) !== v) raw = String(v);
  });
});

let error = $derived.by<string | null>(() => {
  const trimmed = raw.trim();
  if (!/^\d+$/.test(trimmed)) return t("settings.enterValidNumber");
  const n = Number.parseInt(trimmed, 10);
  if (n < min || n > max) {
    return t("settings.mustBeBetween", { min: min, max: max });
  }
  return null;
});

// Width the number field to its largest possible value so the stepper stays
// compact instead of stretching to the input's default intrinsic width.
let fieldWidth = $derived.by(() => `${String(max).length + 1}ch`);

let decrementLabel = $derived.by(() => (step === 1 ? "−" : `−${step}${suffix}`));
let incrementLabel = $derived.by(() => (step === 1 ? "+" : `+${step}${suffix}`));
let decrementAriaLabel = $derived.by(() => t("settings.decrease", { label: label }));
let incrementAriaLabel = $derived.by(() => t("settings.increase", { label: label }));

function decrement() {
  const next = modelValue - step;
  if (next >= min) modelValue = next;
}

function increment() {
  const next = modelValue + step;
  if (next <= max) modelValue = next;
}

function onInput(event: Event) {
  raw = (event.target as HTMLInputElement).value;
  if (!error) modelValue = Number.parseInt(raw, 10);
}

// Settle on a valid integer when focus leaves: clamp into range (or fall back
// to the last valid model value) and resync the displayed text.
function onBlur() {
  const parsed = Number.parseInt(raw, 10);
  const next = Number.isFinite(parsed) ? Math.min(max, Math.max(min, parsed)) : modelValue;
  modelValue = next;
  raw = String(next);
}
</script>

<div class="stepper-field">
  <!-- biome-ignore lint/a11y/useSemanticElements: role=group + aria-label names the button/field cluster; no native element fits -->
  <div class="stepper" role="group" aria-label={label}>
    <button
      class={["stepper__btn", step === 1 ? "stepper__btn--lg" : "stepper__btn--sm"]}
      type="button"
      disabled={modelValue <= min}
      aria-label={decrementAriaLabel}
      onclick={decrement}
    >
      {decrementLabel}
    </button>
    <span class="stepper__value">
      <input
        class="stepper__field"
        type="text"
        inputmode="numeric"
        style:width={fieldWidth}
        value={raw}
        aria-label={label}
        aria-invalid={error ? "true" : undefined}
        oninput={onInput}
        onblur={onBlur}
      >
      {#if suffix}
        <span class="stepper__suffix">{suffix}</span>
      {/if}</span
    >
    <button
      class={["stepper__btn", step === 1 ? "stepper__btn--lg" : "stepper__btn--sm"]}
      type="button"
      disabled={modelValue >= max}
      aria-label={incrementAriaLabel}
      onclick={increment}
    >
      {incrementLabel}
    </button>
  </div>
  {#if error}
    <p class="stepper-field__error">{error}</p>
  {/if}
</div>

<style>
.stepper-field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.stepper {
  display: flex;
  align-items: stretch;
  overflow: hidden;
  border: 1.5px solid var(--color-ink);
  border-radius: var(--r-button);
  background: var(--color-card);
}
.stepper:focus-within {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.stepper__btn {
  cursor: pointer;
  border: 0;
  background: var(--color-card);
  min-width: 44px;
  min-height: 44px;
  padding: 8px 14px;
  line-height: 1;
  font-weight: 700;
  color: var(--color-primary-text);
  transition: background var(--motion-fast) var(--ease-out);
}
.stepper__btn--lg {
  font-size: 1.125rem;
}
.stepper__btn--sm {
  font-size: 0.8125rem;
}
.stepper__btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-ink) 8%, transparent);
}
.stepper__btn:disabled {
  cursor: not-allowed;
  color: var(--color-ink-muted);
  opacity: 0.5;
}
.stepper__value {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 1px;
  padding: 8px 6px;
  border-inline: 1.5px solid var(--color-ink);
  font-weight: 700;
  color: var(--color-ink);
}
.stepper__field {
  min-width: 0;
  border: 0;
  background: transparent;
  text-align: center;
  font: inherit;
  color: inherit;
}
.stepper__field:focus-visible {
  outline: none;
}
.stepper__suffix {
  flex-shrink: 0;
}
.stepper-field__error {
  margin: 0;
  font-size: var(--text-label-sm);
  color: var(--color-primary-text);
}
</style>
