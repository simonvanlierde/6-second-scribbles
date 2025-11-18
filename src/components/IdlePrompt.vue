<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

const props = defineProps<{ modelValue: number | null }>()
const emit = defineEmits<{
  (e: 'update:modelValue', val: number | null): void
  (e: 'confirm'): void
}>()

const remaining = ref<number>(props.modelValue ?? 0)
let timer: number | null = null

const modalRef = ref<HTMLElement | null>(null)
const confirmBtnRef = ref<HTMLButtonElement | null>(null)

watch(
  () => props.modelValue,
  (val) => {
    if (val && val > 0) {
      remaining.value = Math.ceil(val / 1000)
      startCountdown()
      // focus the confirm button when showing
      nextTick(() => confirmBtnRef.value?.focus())
    } else {
      stopCountdown()
    }
  },
  { immediate: true }
)

function startCountdown() {
  stopCountdown()
  timer = window.setInterval(() => {
    remaining.value = Math.max(0, remaining.value - 1)
    if (remaining.value <= 0) {
      stopCountdown()
      emit('update:modelValue', null)
    }
  }, 1000)
}

function stopCountdown() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

function onConfirm() {
  emit('confirm')
  emit('update:modelValue', null)
}

function onKeyDown(e: KeyboardEvent) {
  if (!modalRef.value) return
  const focusable = modalRef.value.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  const first = focusable[0]
  const last = focusable[focusable.length - 1]

  if (e.key === 'Tab') {
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault()
        last?.focus()
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault()
        first?.focus()
      }
    }
  }

  // Prevent accidental dismiss on Escape; we won't confirm on esc.
  if (e.key === 'Escape') {
    e.preventDefault()
    // keep modal visible; focus confirm button
    confirmBtnRef.value?.focus()
  }
}

onMounted(() => {
  // trap keyboard navigation while modal is open
  window.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  stopCountdown()
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div
    v-if="modelValue"
    class="modal-overlay"
    role="dialog"
    aria-modal="true"
    aria-labelledby="idle-title"
    aria-describedby="idle-desc"
  >
    <div class="modal-content" ref="modalRef">
      <div style="display: flex; gap: 0.75rem; align-items: center">
        <!-- Simple activity icon -->
        <svg
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden
        >
          <rect x="2" y="2" width="20" height="20" rx="6" fill="#667eea" />
          <path d="M8 12h8" stroke="#fff" stroke-width="2" stroke-linecap="round" />
          <path d="M8 16h5" stroke="#fff" stroke-width="2" stroke-linecap="round" />
        </svg>
        <div>
          <h2 id="idle-title">Still there?</h2>
          <p id="idle-desc">
            You seem idle. You'll be removed from the room in
            <strong>{{ remaining }}</strong> seconds unless you confirm.
          </p>
        </div>
      </div>
      <div class="modal-actions">
        <button class="btn btn-primary" ref="confirmBtnRef" @click="onConfirm">
          Yes, I'm here
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}
.modal-content {
  background: white;
  padding: 1.25rem 1.5rem;
  border-radius: 12px;
  max-width: 520px;
  width: 100%;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);
}
.modal-content h2 {
  margin: 0 0 0.25rem 0;
}
.modal-content p {
  margin: 0;
  color: #444;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 1rem;
}
.btn.btn-primary {
  background: #667eea;
  color: white;
  padding: 0.6rem 0.9rem;
  border-radius: 8px;
  font-weight: 700;
}
.btn.btn-primary:focus {
  outline: 3px solid rgba(102, 126, 234, 0.25);
}
</style>
