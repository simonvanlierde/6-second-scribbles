<script setup lang="ts">
type Variant = "default" | "ghost";

interface Props {
  label: string;
  // Optional hover tooltip; falls back to `label` when omitted.
  title?: string;
  variant?: Variant;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  title: undefined,
  variant: "default",
  disabled: false,
});

defineEmits<{ click: [MouseEvent] }>();
</script>

<template>
  <button
    type="button"
    class="hd-icon-btn"
    :class="`hd-icon-btn--${props.variant}`"
    :aria-label="props.label"
    :title="props.title ?? props.label"
    :disabled="props.disabled"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.hd-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: var(--r-pill);
  cursor: pointer;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-icon-btn--default {
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  box-shadow: var(--shadow-pill);
  transform: rotate(-1deg);
}
.hd-icon-btn--default:active:not(:disabled) {
  transform: rotate(-1deg) translate(2px, 2px);
  box-shadow: 0 0 0 var(--color-ink);
}
.hd-icon-btn--ghost {
  background: transparent;
  color: var(--color-ink);
  border: 0;
  box-shadow: none;
}
.hd-icon-btn--ghost:hover:not(:disabled) {
  background: rgba(0, 0, 0, 0.04);
}
.hd-icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.hd-icon-btn :slotted(svg) {
  width: 20px;
  height: 20px;
}
</style>
