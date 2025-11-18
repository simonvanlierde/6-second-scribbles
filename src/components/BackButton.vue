<script setup lang="ts">
import { useRouter } from 'vue-router'

interface Props {
  to?: string
  label?: string
  variant?: 'default' | 'light'
}

const props = withDefaults(defineProps<Props>(), {
  to: '/',
  label: 'Back',
  variant: 'default',
})

const router = useRouter()

function goBack() {
  if (props.to) {
    router.push(props.to)
  } else {
    router.back()
  }
}
</script>

<template>
  <button class="back-button" :class="`variant-${variant}`" @click="goBack" :title="`Go ${label}`">
    <svg class="back-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
    </svg>
    <span class="back-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.back-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1rem;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.back-button:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateX(-3px);
}

.back-button.variant-light {
  background: white;
  color: #4a5568;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.back-button.variant-light:hover {
  background: #f8fafc;
  border-color: #cbd5e0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.back-icon {
  display: block;
  flex-shrink: 0;
}

.back-label {
  display: block;
}

@media (max-width: 480px) {
  .back-button {
    padding: 0.5rem 0.875rem;
    font-size: 0.9rem;
  }
}
</style>
