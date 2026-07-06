<script setup lang="ts">
import { computed } from "vue";

interface Option {
  value: string;
  label: string;
}

interface Props {
  modelValue: string;
  options: Option[];
  name?: string;
  ariaLabel?: string;
}

const props = withDefaults(defineProps<Props>(), {
  name: undefined,
  ariaLabel: undefined,
});

const emit = defineEmits<{ "update:modelValue": [string] }>();

// Fallback group name if not supplied — stable within the component lifetime.
const groupName = computed(() => props.name ?? `hd-seg-${(Math.random() * 1e6) | 0}`);

function onChange(value: string): void {
  emit("update:modelValue", value);
}
</script>

<template>
  <div class="hd-seg" role="radiogroup" :aria-label="props.ariaLabel">
    <!-- biome-ignore lint/a11y/noLabelWithoutControl: wraps the radio input and its text; Biome misses controls inside v-for labels -->
    <label
      v-for="opt in props.options"
      :key="opt.value"
      class="hd-seg__item"
      :class="{ 'hd-seg__item--active': opt.value === props.modelValue }"
    >
      <input
        type="radio"
        class="hd-seg__input"
        :name="groupName"
        :value="opt.value"
        :checked="opt.value === props.modelValue"
        @change="onChange(opt.value)"
      >
      <span class="hd-seg__label">{{ opt.label }}</span>
    </label>
  </div>
</template>

<style scoped>
.hd-seg {
  display: inline-flex;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-pill);
  box-shadow: var(--shadow-pill);
  overflow: hidden;
  background: var(--color-card);
}
.hd-seg__item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  color: var(--color-ink);
  cursor: pointer;
  min-height: 44px;
}
.hd-seg__item + .hd-seg__item {
  border-left: 1.5px solid var(--color-ink);
}
.hd-seg__input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.hd-seg__item--active {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
.hd-seg__item:focus-within {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
</style>
