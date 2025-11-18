<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from 'vue'

import { ALLOWED_CHARS } from '@/shared/roomCode'

const props = defineProps({
  modelValue: { type: String, default: '' },
  length: { type: Number, default: 6 },
})

const emit = defineEmits(['update:modelValue', 'complete', 'enter'])

const codeInputs = ref<string[]>(Array.from({ length: props.length }, () => ''))
const inputRefs: Array<HTMLInputElement | null> = []
const liveAnnouncement = ref('')

const combined = computed(() => codeInputs.value.join(''))

watch(
  () => props.modelValue,
  (v) => {
    if (v == null) return
    const clean = (v || '').toUpperCase().replace(/\s+/g, '').slice(0, props.length)
    for (let i = 0; i < props.length; i++) codeInputs.value[i] = clean[i] || ''
  }
)

watch(combined, (val) => {
  emit('update:modelValue', val)
  if (val.length === props.length) {
    emit('complete', val)
    liveAnnouncement.value = `Room code ${val} entered` // screen reader announcement
  }
})

function setRef(el: unknown, idx: number) {
  inputRefs[idx] = (el as HTMLInputElement) || null
}

function focusInput(idx: number) {
  nextTick(() => {
    const el = inputRefs[idx]
    if (el) el.focus()
  })
}

function onInput(e: Event, idx: number) {
  const value = ((e.target as HTMLInputElement).value || '').toUpperCase().replace(/\s+/g, '')
  const char = value.slice(-1)
  if (char && ALLOWED_CHARS.includes(char)) {
    codeInputs.value[idx] = char
    if (idx < props.length - 1) focusInput(idx + 1)
  } else {
    codeInputs.value[idx] = ''
    const el = inputRefs[idx]
    if (el) el.value = ''
  }
}

function onKeyDown(e: KeyboardEvent, idx: number) {
  if (e.key === 'Backspace') {
    if (codeInputs.value[idx]) {
      codeInputs.value[idx] = ''
    } else if (idx > 0) {
      codeInputs.value[idx - 1] = ''
      focusInput(idx - 1)
    }
  } else if (e.key === 'ArrowLeft') {
    focusInput(Math.max(idx - 1, 0))
  } else if (e.key === 'ArrowRight') {
    focusInput(Math.min(idx + 1, props.length - 1))
  }

  // If Enter is pressed and code is complete, emit complete
  if (e.key === 'Enter') {
    const val = combined.value
    if (val.length === props.length) {
      emit('enter', val)
    }
  }
}

function onPaste(e: ClipboardEvent) {
  const paste = e.clipboardData?.getData('text') || ''
  const cleaned = paste.replace(/\s+/g, '').toUpperCase()
  const chars = cleaned
    .split('')
    .filter((c) => ALLOWED_CHARS.includes(c))
    .slice(0, props.length)
  for (let i = 0; i < props.length; i++) {
    codeInputs.value[i] = chars[i] || ''
  }
  const firstEmpty = codeInputs.value.findIndex((c) => !c)
  focusInput(firstEmpty === -1 ? props.length - 1 : firstEmpty)
}

onMounted(() => {
  // initialize from modelValue
  if (props.modelValue) {
    const clean = props.modelValue.toUpperCase().replace(/\s+/g, '').slice(0, props.length)
    for (let i = 0; i < props.length; i++) codeInputs.value[i] = clean[i] || ''
  }
})
</script>

<template>
  <div class="room-code-inputs" @paste.prevent="onPaste">
    <template v-for="(val, i) in codeInputs" :key="i">
      <input
        class="code-input"
        :ref="(el) => setRef(el, i)"
        :value="codeInputs[i]"
        @input="(e) => onInput(e, i)"
        @keydown="(e) => onKeyDown(e, i)"
        maxlength="1"
        inputmode="text"
        aria-label="Room code digit {{ i + 1 }} of {{ codeInputs.length }}"
      />
    </template>
    <div class="sr-only" aria-live="polite">{{ liveAnnouncement }}</div>
  </div>
</template>

<!-- styles moved to src/assets/main.css -->

<style scoped>
.room-code-inputs {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  align-items: center;
  margin-top: 0.5rem;
}
.code-input {
  width: 2.25rem;
  height: 2.75rem;
  text-align: center;
  font-size: 1.25rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  outline: none;
}
.code-input:focus {
  border-color: #5b8def;
  box-shadow: 0 0 0 3px rgba(91, 141, 239, 0.12);
}
</style>
