<script setup lang="ts">
type Size = "sm" | "md" | "lg";

interface Props {
  initial: string;
  color: string;
  size?: Size;
  disconnected?: boolean;
}

const props = withDefaults(defineProps<Props>(), { size: "md", disconnected: false });
// NOTE: the color goes through :style, which Vue applies via the CSSOM. The CSP
// (frontend/Caddyfile) blocks a literal style attribute without 'unsafe-inline'.
</script>

<template>
  <span
    class="hd-avatar"
    :style="{ background: props.color }"
    :class="[`hd-avatar--${props.size}`, { 'hd-avatar--disconnected': props.disconnected }]"
    aria-hidden="true"
  >
    {{ props.initial }}
  </span>
</template>

<style scoped>
.hd-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-ink);
  border-radius: var(--r-avatar);
  box-shadow: var(--shadow-avatar);
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--color-ink-fixed);
  flex-shrink: 0;
  user-select: none;
}
.hd-avatar--disconnected {
  filter: grayscale(1);
  opacity: 0.45;
}
.hd-avatar--sm {
  width: 28px;
  height: 28px;
  font-size: 0.8rem;
}
.hd-avatar--md {
  width: 36px;
  height: 36px;
  font-size: 0.95rem;
}
.hd-avatar--lg {
  width: 64px;
  height: 64px;
  font-size: 1.6rem;
  border-radius: 22px 28px 18px 24px;
  box-shadow: 4px 4px 0 var(--color-ink);
}
</style>
