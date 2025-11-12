<template>
  <div class="toast-root" aria-live="polite">
    <div v-for="n in notifications" :key="n.id" class="toast-item">{{ n.text }}</div>
  </div>
</template>

<script setup lang="ts">
import { useNotifications } from '@/composables/notifications'
const { notifications } = useNotifications()
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
  background: rgba(0, 0, 0, 0.75);
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.95rem;
}
</style>
