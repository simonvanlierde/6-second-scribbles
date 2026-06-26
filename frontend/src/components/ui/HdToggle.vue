<script setup lang="ts">
interface Props {
  modelValue: boolean;
  label?: string;
  // Optional helper text shown as a hover/focus tooltip on an info icon.
  help?: string;
}

const props = withDefaults(defineProps<Props>(), {
  label: undefined,
  help: undefined,
});

const emit = defineEmits<{
  "update:modelValue": [boolean];
  change: [Event];
}>();

function onChange(event: Event) {
  emit("update:modelValue", (event.target as HTMLInputElement).checked);
  emit("change", event);
}
</script>

<template>
  <label class="hd-toggle">
    <span v-if="props.label" class="hd-toggle__label">
      {{ props.label }}
      <span
        v-if="props.help"
        class="hd-toggle__info"
        role="img"
        tabindex="0"
        :title="props.help"
        :aria-label="props.help"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
      </span>
    </span>
    <span class="hd-toggle__switch">
      <input
        type="checkbox"
        class="hd-toggle__input"
        :checked="props.modelValue"
        :aria-label="props.label"
        @change="onChange"
      >
      <span class="hd-toggle__track" aria-hidden="true" />
    </span>
  </label>
</template>

<style scoped>
.hd-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.hd-toggle__label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: var(--text-label-md);
  font-weight: 600;
  color: var(--color-ink);
}
.hd-toggle__info {
  display: inline-flex;
  color: var(--color-ink-muted);
  cursor: help;
  border-radius: var(--r-pill);
}
.hd-toggle__info svg {
  width: 14px;
  height: 14px;
}
.hd-toggle__info:focus-visible {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
.hd-toggle__switch {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}
.hd-toggle__input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
}
.hd-toggle__track {
  position: relative;
  display: block;
  width: 40px;
  height: 20px;
  border-radius: var(--r-pill);
  background: color-mix(in srgb, var(--color-ink) 28%, transparent);
  transition: background var(--motion-fast) var(--ease-out);
}
.hd-toggle__track::after {
  content: "";
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--color-card);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: transform var(--motion-fast) var(--ease-spring);
}
.hd-toggle__input:checked + .hd-toggle__track {
  background: var(--color-marker-red);
}
.hd-toggle__input:checked + .hd-toggle__track::after {
  transform: translateX(20px);
}
.hd-toggle__input:focus-visible + .hd-toggle__track {
  outline: 3px solid var(--color-ring);
  outline-offset: 2px;
}
</style>
