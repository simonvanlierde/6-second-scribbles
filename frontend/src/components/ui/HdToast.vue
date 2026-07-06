<script setup lang="ts">
import { useNotifications } from "@/composables/notifications";

const { notifications } = useNotifications();
</script>

<template>
  <!-- The stack owns the single live region; per-toast role="status" here would
       make each notification announce twice. -->
  <div class="hd-toast-stack" role="status" aria-live="polite">
    <div v-for="n in notifications" :key="n.id" class="hd-toast" :class="`hd-toast--${n.type}`">{{ n.text }}</div>
  </div>
</template>

<style scoped>
.hd-toast-stack {
  position: fixed;
  top: 16px;
  right: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 1000;
  pointer-events: none;
}
.hd-toast {
  pointer-events: auto;
  padding: 10px 14px;
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2px solid var(--color-ink);
  border-radius: 14px 18px 12px 16px;
  box-shadow: var(--shadow-card);
  max-width: 320px;
}
.hd-toast--success {
  background: var(--color-meadow-green);
  color: var(--color-ink-fixed);
}
.hd-toast--error {
  background: var(--color-primary-strong);
  color: white;
}
.hd-toast--info {
  background: var(--color-highlighter-yellow);
  color: var(--color-ink-fixed);
}
</style>
