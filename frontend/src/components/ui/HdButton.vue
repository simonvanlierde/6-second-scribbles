<script setup lang="ts">
type Variant = "primary" | "secondary" | "success" | "ghost";

interface Props {
  variant?: Variant;
  type?: "button" | "submit";
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  variant: "primary",
  type: "button",
  disabled: false,
});

defineEmits<{ click: [MouseEvent] }>();
</script>

<template>
  <button
    :type="props.type"
    :disabled="props.disabled"
    class="hd-btn"
    :class="`hd-btn--${props.variant}`"
    @click="$emit('click', $event)"
  >
    <slot />
  </button>
</template>

<style scoped>
.hd-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 18px;
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1.05rem;
  line-height: 1;
  border: var(--border-button) solid var(--color-ink);
  border-radius: var(--r-button);
  box-shadow: var(--shadow-button);
  transform: rotate(var(--rotate-button));
  cursor: pointer;
  min-height: 44px;
  min-width: 44px;
  transition:
    transform var(--motion-fast) var(--ease-spring),
    box-shadow var(--motion-fast) var(--ease-spring);
}
.hd-btn:active:not(:disabled) {
  transform: rotate(var(--rotate-button)) translate(3px, 3px);
  box-shadow: 0 0 0 var(--color-ink);
}
.hd-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.hd-btn--primary {
  background: var(--color-marker-red);
  color: white;
}
.hd-btn--secondary {
  background: var(--color-card);
  color: var(--color-ink);
  --rotate-button: 0.4deg;
}
.hd-btn--success {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
  --rotate-button: -0.3deg;
  border-radius: 12px 18px 14px 22px;
}
.hd-btn--ghost {
  background: transparent;
  color: var(--color-ballpoint-blue);
  border: 0;
  box-shadow: none;
  text-decoration: underline wavy;
  text-underline-offset: 4px;
  transform: none;
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 1rem;
  padding: 8px 12px;
}
.hd-btn--ghost:active:not(:disabled) {
  transform: none;
}
</style>
