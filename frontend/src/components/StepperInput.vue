<script setup lang="ts">
import { computed } from "vue";

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

// Typing: push raw integers straight through so the parent's existing
// validation (e.g. the rounds range check) can react. Out-of-range values are
// clamped on blur so the field always settles on a valid positive integer.
function onInput(event: Event) {
  const parsed = Number.parseInt((event.target as HTMLInputElement).value, 10);
  if (Number.isFinite(parsed)) modelValue.value = parsed;
}

function onBlur(event: Event) {
  const parsed = Number.parseInt((event.target as HTMLInputElement).value, 10);
  modelValue.value = Number.isFinite(parsed) ? Math.min(props.max, Math.max(props.min, parsed)) : props.min;
}
</script>

<template>
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
        :value="modelValue"
        :aria-label="label"
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
</template>

<style scoped>
.stepper {
  display: flex;
  max-width: 200px;
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
  flex: 1;
  min-width: 48px;
  align-items: center;
  justify-content: center;
  gap: 1px;
  padding: 8px 4px;
  border-inline: 1.5px solid var(--color-ink);
  font-weight: 700;
  color: var(--color-ink);
}
.stepper__field {
  width: 100%;
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
</style>
