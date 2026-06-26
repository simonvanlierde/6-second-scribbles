<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";

const props = withDefaults(
  defineProps<{
    label: string;
    min: number;
    max: number;
    step?: number;
    suffix?: string;
  }>(),
  { step: 1, suffix: "" },
);

const modelValue = defineModel<number>({ required: true });

const { t } = useI18n();

// Local editable string so invalid/in-progress text (letters, empty, out of
// range) can be shown to the user while we only push valid integers upward.
const raw = ref(String(modelValue.value));
watch(modelValue, (v) => {
  if (Number.parseInt(raw.value, 10) !== v) raw.value = String(v);
});

const error = computed<string | null>(() => {
  const trimmed = raw.value.trim();
  if (!/^\d+$/.test(trimmed)) return t("settings.enterValidNumber");
  const n = Number.parseInt(trimmed, 10);
  if (n < props.min || n > props.max) {
    return t("settings.mustBeBetween", { min: props.min, max: props.max });
  }
  return null;
});

// Width the number field to its largest possible value so the stepper stays
// compact instead of stretching to the input's default intrinsic width.
const fieldWidth = computed(() => `${String(props.max).length + 1}ch`);

const decrementLabel = computed(() => (props.step === 1 ? "−" : `−${props.step}${props.suffix}`));
const incrementLabel = computed(() => (props.step === 1 ? "+" : `+${props.step}${props.suffix}`));
const decrementAriaLabel = computed(() => `Decrease ${props.label}`);
const incrementAriaLabel = computed(() => `Increase ${props.label}`);

function decrement() {
  const next = modelValue.value - props.step;
  if (next >= props.min) modelValue.value = next;
}

function increment() {
  const next = modelValue.value + props.step;
  if (next <= props.max) modelValue.value = next;
}

function onInput(event: Event) {
  raw.value = (event.target as HTMLInputElement).value;
  if (!error.value) modelValue.value = Number.parseInt(raw.value, 10);
}

// Settle on a valid integer when focus leaves: clamp into range (or fall back
// to the last valid model value) and resync the displayed text.
function onBlur() {
  const parsed = Number.parseInt(raw.value, 10);
  const next = Number.isFinite(parsed) ? Math.min(props.max, Math.max(props.min, parsed)) : modelValue.value;
  modelValue.value = next;
  raw.value = String(next);
}
</script>

<template>
  <div class="stepper-field">
    <div class="stepper" role="group" :aria-label="label">
      <button
        type="button"
        class="stepper__btn"
        :class="step === 1 ? 'stepper__btn--lg' : 'stepper__btn--sm'"
        :disabled="modelValue <= min"
        :aria-label="decrementAriaLabel"
        @click="decrement"
      >
        {{ decrementLabel }}
      </button>
      <span class="stepper__value">
        <input
          class="stepper__field"
          type="text"
          inputmode="numeric"
          :style="{ width: fieldWidth }"
          :value="raw"
          :aria-label="label"
          :aria-invalid="error ? 'true' : undefined"
          @input="onInput"
          @blur="onBlur"
        >
        <span v-if="suffix" class="stepper__suffix">{{ suffix }}</span>
      </span>
      <button
        type="button"
        class="stepper__btn"
        :class="step === 1 ? 'stepper__btn--lg' : 'stepper__btn--sm'"
        :disabled="modelValue >= max"
        :aria-label="incrementAriaLabel"
        @click="increment"
      >
        {{ incrementLabel }}
      </button>
    </div>
    <p v-if="error" class="stepper-field__error">{{ error }}</p>
  </div>
</template>

<style scoped>
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
  padding: 8px 14px;
  line-height: 1;
  font-weight: 700;
  color: var(--color-marker-red);
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
  color: var(--color-marker-red);
}
</style>
