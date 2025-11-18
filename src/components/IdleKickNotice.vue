<template>
  <div v-if="message" class="idle-kick-notice" role="alert">
    <div class="notice-content">
      <strong>Removed due to inactivity</strong>
      <p>{{ message }}</p>
    </div>
    <button class="btn" @click="$emit('dismiss')">Dismiss</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ message: string | null }>()
defineEmits<{ (e: 'dismiss'): void }>()
</script>

<style scoped>
.idle-kick-notice {
  position: fixed;
  right: 1rem;
  bottom: 1rem;
  background: #fff6f6;
  color: #611a15;
  border: 1px solid #f5c6cb;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  display: flex;
  gap: 0.75rem;
  align-items: center;
  z-index: 2500;
}
.notice-content p {
  margin: 0;
}
.btn {
  background: transparent;
  border: 1px solid #ccc;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
}
</style>
