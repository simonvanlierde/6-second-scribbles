<script setup lang="ts">
type Variant = "default" | "postit";

interface Props {
  variant?: Variant;
}

const props = withDefaults(defineProps<Props>(), { variant: "default" });
</script>

<template>
  <div class="hd-card" :class="`hd-card--${props.variant}`"><slot /></div>
</template>

<style scoped>
.hd-card {
  padding: var(--space-4);
  border: var(--border-card) solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  transform: rotate(var(--rotate-card));
}
.hd-card--default {
  background: var(--color-card);
}
.hd-card--postit {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
  --rotate-card: var(--rotate-postit);
  border-width: 1px;
  border-color: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  box-shadow: 2px 4px 6px rgba(0, 0, 0, 0.16);
  font-size: 0.95rem;
}
</style>
