<script setup lang="ts">
import { nextTick, ref, watch } from "vue";

const open = defineModel<boolean>("open", { default: false });
const modelValue = defineModel<string>({ default: "" });

const props = withDefaults(
  defineProps<{
    descriptionKey?: string;
  }>(),
  {
    descriptionKey: "roomEntry.needNameText",
  },
);

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

const dialogRef = ref<HTMLDialogElement | null>(null);
const inputRef = ref<HTMLInputElement | null>(null);

watch(
  open,
  async (isOpen) => {
    const el = dialogRef.value;
    if (!el) return;
    if (isOpen && !el.open) {
      if (typeof el.showModal === "function") {
        el.showModal();
      } else {
        el.setAttribute("open", "");
      }
      await nextTick();
      inputRef.value?.focus();
      inputRef.value?.select();
    } else if (!isOpen && el.open) {
      if (typeof el.close === "function") {
        el.close();
      } else {
        el.removeAttribute("open");
      }
    }
  },
  { flush: "post" },
);

function onCancel() {
  open.value = false;
  emit("cancel");
}

function onClose() {
  if (open.value) {
    open.value = false;
    emit("cancel");
  }
}

function onConfirm() {
  if (!modelValue.value.trim()) return;
  modelValue.value = modelValue.value.trim();
  open.value = false;
  emit("confirm");
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="fixed top-1/2 left-1/2 m-0 w-[calc(100%-2rem)] max-w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-[28px] border border-white/30 bg-white p-6 shadow-[0_28px_80px_rgba(15,23,42,0.26)] backdrop:bg-black/45 backdrop:backdrop-blur-[3px]"
    @click.self="onCancel"
    @close="onClose"
  >
    <div class="space-y-4">
      <div class="space-y-1.5">
        <h2 class="m-0 text-[1.5rem] font-bold text-slate-900">{{ $t("home.yourName") }}</h2>
        <p class="m-0 text-sm leading-relaxed text-slate-500">{{ $t(props.descriptionKey) }}</p>
      </div>

      <input
        ref="inputRef"
        v-model="modelValue"
        type="text"
        class="block w-full rounded-[20px] border border-slate-300 bg-white px-4 py-3.5 text-base text-slate-800 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)] transition-[border-color,box-shadow] focus:border-primary focus:shadow-[0_0_0_4px_rgba(102,126,234,0.12)] focus:outline-none"
        :placeholder="$t('home.enterYourName')"
        maxlength="20"
        data-testid="name-prompt-input"
        @keyup.enter="onConfirm"
      >

      <div class="flex justify-end gap-3">
        <button
          type="button"
          class="cursor-pointer rounded-[16px] border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50"
          @click="onCancel"
        >
          {{ $t("lobby.cancel") }}
        </button>
        <button
          type="button"
          class="cursor-pointer rounded-[16px] border-0 bg-gradient-to-br from-primary to-secondary px-5 py-2.5 text-sm font-semibold text-white transition-[transform,filter] hover:-translate-y-px hover:brightness-[1.05] disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!modelValue.trim()"
          data-testid="name-prompt-confirm"
          @click="onConfirm"
        >
          {{ $t("roomEntry.continue") }}
        </button>
      </div>
    </div>
  </dialog>
</template>
