<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { ALLOWED_CHARS } from "@/shared/roomCode";

const props = defineProps({
  modelValue: { type: String, default: "" },
  length: { type: Number, default: 6 },
});

const emit = defineEmits(["update:modelValue", "complete", "submit"]);

const codeInputs = ref<string[]>(Array.from({ length: props.length }, () => ""));
const inputRefs: Array<HTMLInputElement | null> = [];
const liveAnnouncement = ref("");

const combined = computed(() => codeInputs.value.join(""));

watch(
  () => props.modelValue,
  (v) => {
    if (v == null) return;
    const clean = (v || "").toUpperCase().replace(/\s+/g, "").slice(0, props.length);
    for (let i = 0; i < props.length; i++) codeInputs.value[i] = clean[i] || "";
  },
);

watch(combined, (val) => {
  emit("update:modelValue", val);
  if (val.length === props.length) {
    emit("complete", val);
    liveAnnouncement.value = `Room code ${val} entered`; // screen reader announcement
  }
});

function setRef(el: unknown, idx: number) {
  inputRefs[idx] = (el as HTMLInputElement) || null;
}

function focusInput(idx: number) {
  nextTick(() => {
    const el = inputRefs[idx];
    if (el) el.focus();
  });
}

function onInput(e: Event, idx: number) {
  const value = ((e.target as HTMLInputElement).value || "").toUpperCase().replace(/\s+/g, "");
  const char = value.slice(-1);
  if (char && ALLOWED_CHARS.includes(char)) {
    codeInputs.value[idx] = char;
    if (idx < props.length - 1) focusInput(idx + 1);
  } else {
    codeInputs.value[idx] = "";
    const el = inputRefs[idx];
    if (el) el.value = "";
  }
}

function onKeyDown(e: KeyboardEvent, idx: number) {
  if (e.key === "Backspace") {
    if (codeInputs.value[idx]) {
      codeInputs.value[idx] = "";
    } else if (idx > 0) {
      codeInputs.value[idx - 1] = "";
      focusInput(idx - 1);
    }
  } else if (e.key === "ArrowLeft") {
    focusInput(Math.max(idx - 1, 0));
  } else if (e.key === "ArrowRight") {
    focusInput(Math.min(idx + 1, props.length - 1));
  } else if (e.key === "Enter") {
    e.preventDefault();
    // Bubble a submit event so parent can decide what to do (join, focus name, etc.)
    emit("submit");
  }
}

function onPaste(e: ClipboardEvent) {
  const paste = e.clipboardData?.getData("text") || "";
  const cleaned = paste.replace(/\s+/g, "").toUpperCase();
  const chars = cleaned
    .split("")
    .filter((c) => ALLOWED_CHARS.includes(c))
    .slice(0, props.length);
  for (let i = 0; i < props.length; i++) {
    codeInputs.value[i] = chars[i] || "";
  }
  const firstEmpty = codeInputs.value.findIndex((c) => !c);
  focusInput(firstEmpty === -1 ? props.length - 1 : firstEmpty);
}

onMounted(() => {
  // initialize from modelValue
  if (props.modelValue) {
    const clean = props.modelValue.toUpperCase().replace(/\s+/g, "").slice(0, props.length);
    for (let i = 0; i < props.length; i++) codeInputs.value[i] = clean[i] || "";
  }
});
</script>

<template>
  <div
    class="flex w-full max-w-full items-center justify-center gap-1.5 overflow-hidden max-[480px]:gap-[0.35rem] max-[480px]:px-0"
    @paste.prevent="onPaste"
  >
    <template v-for="(val, i) in codeInputs" :key="i">
      <input
        :ref="(el) => setRef(el, i)"
        class="code-input h-[3.2rem] w-[2.9rem] min-w-0 max-w-[3.4rem] flex-[1_1_0] rounded-lg border border-[#ccc] bg-white py-[0.15rem] text-center font-mono text-base leading-[1.1rem] transition-[border-color,box-shadow,transform] duration-150 ease-out focus:border-[#5b8def] focus:outline-none focus:shadow-[0_0_0_3px_rgba(91,141,239,0.12)] max-[480px]:h-[3.15rem] max-[480px]:w-full max-[480px]:max-w-none max-[480px]:text-[1rem]"
        :value="codeInputs[i]"
        maxlength="1"
        inputmode="text"
        autocapitalize="characters"
        autocorrect="off"
        spellcheck="false"
        pattern="[A-Za-z0-9]*"
        aria-label="Room code digit {{ i + 1 }} of {{ codeInputs.length }}"
        @input="(e) => onInput(e, i)"
        @keydown="(e) => onKeyDown(e, i)"
      >
    </template>
    <div class="sr-only" aria-live="polite">{{ liveAnnouncement }}</div>
  </div>
</template>
