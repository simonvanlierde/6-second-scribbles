<template>
  <div class="toast-root" aria-live="polite">
    <div v-for="n in notifications" :key="n.id" :class="['toast-item', `toast-${n.type}`]">{{ n.text }}</div>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from "@/composables/notifications";

const { notifications } = useNotifications();
</script>

<style scoped>
.toast-root {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast-item {
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm);
  font-size: 0.95rem;
}

.toast-info {
  background: rgba(0, 0, 0, 0.75);
}
.toast-success {
  background: var(--color-success-dark);
}
.toast-error {
  background: var(--color-danger);
}
</style>
