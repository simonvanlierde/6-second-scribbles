<script setup lang="ts">
import { ref, watch } from "vue";

interface Props {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "primary";
}

const props = withDefaults(defineProps<Props>(), {
  message: "",
  confirmLabel: "Confirm",
  cancelLabel: "Cancel",
  variant: "danger",
});

const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ confirm: []; cancel: [] }>();

const dialogRef = ref<HTMLDialogElement | null>(null);

watch(
  open,
  (isOpen) => {
    const el = dialogRef.value;
    if (!el) return;
    if (isOpen && !el.open) el.showModal();
    else if (!isOpen && el.open) el.close();
  },
  { flush: "post" },
);

function onCancel() {
  open.value = false;
  emit("cancel");
}

function onConfirm() {
  open.value = false;
  emit("confirm");
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="fixed top-1/2 left-1/2 m-0 w-[calc(100%-2rem)] max-w-[360px] -translate-x-1/2 -translate-y-1/2 rounded-lg border-0 p-8 shadow-[0_20px_60px_rgba(0,0,0,0.25)] backdrop:bg-black/55 backdrop:backdrop-blur-[2px]"
    @click.self="onCancel"
    @close="onCancel"
  >
    <h2 class="mb-2.5 text-xl text-ink-dark">{{ title }}</h2>
    <p v-if="message" class="mb-6 text-[0.9375rem] text-ink-muted">{{ message }}</p>
    <div class="flex justify-end gap-3">
      <button
        type="button"
        class="cursor-pointer rounded-md border-[1.5px] border-slate-300 bg-transparent px-5 py-2 text-[0.9375rem] font-semibold text-ink-dark transition-all duration-150 hover:border-slate-400 hover:bg-slate-50"
        @click="onCancel"
      >
        {{ cancelLabel }}
      </button>
      <button
        type="button"
        class="cursor-pointer rounded-md border-0 px-5 py-2 text-[0.9375rem] font-semibold text-white transition-[background,filter] duration-150"
        :class="
          props.variant === 'primary'
            ? 'bg-gradient-to-br from-primary to-secondary hover:brightness-110'
            : 'bg-danger hover:bg-danger-dark'
        "
        @click="onConfirm"
      >
        {{ confirmLabel }}
      </button>
    </div>
  </dialog>
</template>
