<script setup lang="ts">
import { watch } from 'vue'

const props = defineProps<{ modelValue: string; duration?: number }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

watch(
  () => props.modelValue,
  (val) => {
    if (val && val.length > 0) {
      window.setTimeout(() => emit('update:modelValue', ''), props.duration ?? 3500)
    }
  }
)
</script>

<template>
  <transition name="fade-slide">
    <div v-if="modelValue" class="inline-alert" role="status" aria-live="polite">
      <slot />
    </div>
  </transition>
</template>

<style scoped>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity 260ms ease,
    transform 260ms ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
.inline-alert {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  padding: 0.4rem 0.75rem;
  font-weight: 600;
  color: #333;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
}
</style>
