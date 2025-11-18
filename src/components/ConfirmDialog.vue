<script setup lang="ts">
import {
  ref,
  withDefaults,
  defineProps,
  defineEmits,
  onMounted,
  onUnmounted,
  nextTick,
  watch,
} from 'vue'

type Props = {
  modelValue: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm',
  message: '',
  confirmText: 'Leave',
  cancelText: 'Cancel',
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm'): void
}>()

const confirmBtn = ref<HTMLButtonElement | null>(null)

function close() {
  emit('update:modelValue', false)
}

function onConfirm() {
  emit('confirm')
  emit('update:modelValue', false)
}

function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
  } else if (e.key === 'Enter') {
    onConfirm()
  }
}

watch(
  () => props.modelValue,
  async (val) => {
    if (val) {
      await nextTick()
      confirmBtn.value?.focus()
    }
  }
)

onMounted(() => document.addEventListener('keydown', onKeyDown))
onUnmounted(() => document.removeEventListener('keydown', onKeyDown))
</script>

<template>
  <div v-if="props.modelValue" class="modal-overlay" @click="close" role="dialog" aria-modal="true">
    <div class="modal-content" @click.stop>
      <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem">
        <slot name="icon" />
        <h2 style="margin: 0">{{ props.title }}</h2>
      </div>
      <p v-if="props.message">{{ props.message }}</p>
      <div class="modal-actions">
        <button class="btn btn-secondary" @click="close">{{ props.cancelText }}</button>
        <button ref="confirmBtn" class="btn btn-danger" @click="onConfirm">
          {{ props.confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-content h2 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
}

.modal-content p {
  margin-bottom: 1.5rem;
  color: #666;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-danger {
  background-color: #dc3545;
  color: white;
}

.btn-danger:hover {
  background-color: #c82333;
}
</style>
