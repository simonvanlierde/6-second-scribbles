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
</script>

<template>
  <div
    class="flex max-w-[200px] items-stretch overflow-hidden rounded-md border-[1.5px] border-slate-200"
    role="group"
    :aria-label="label"
  >
    <button
      type="button"
      class="cursor-pointer border-0 bg-surface px-3.5 py-2 leading-none font-bold text-primary transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:text-gray-300"
      :class="step === 1 ? 'text-lg' : 'text-[0.8125rem]'"
      :disabled="modelValue <= min"
      :aria-label="decrementAriaLabel"
      @click="decrement"
    >
      {{ decrementLabel }}
    </button>
    <span class="min-w-12 flex-1 border-x-[1.5px] border-slate-200 px-1 py-2 text-center font-bold text-ink-dark">
      {{ modelValue }}{{ suffix }}
    </span>
    <button
      type="button"
      class="cursor-pointer border-0 bg-surface px-3.5 py-2 leading-none font-bold text-primary transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:text-gray-300"
      :class="step === 1 ? 'text-lg' : 'text-[0.8125rem]'"
      :disabled="modelValue >= max"
      :aria-label="incrementAriaLabel"
      @click="increment"
    >
      {{ incrementLabel }}
    </button>
  </div>
</template>
