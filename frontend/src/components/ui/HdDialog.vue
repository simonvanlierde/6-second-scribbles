<script setup lang="ts">
import { ref, watch } from "vue";

import HdButton from "@/components/ui/HdButton.vue";

interface Props {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "primary" | "danger";
}

const props = withDefaults(defineProps<Props>(), {
  message: "",
  confirmLabel: "Confirm",
  variant: "danger",
  // cancelLabel intentionally has no default
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

function onConfirm(): void {
  open.value = false;
  emit("confirm");
}

function onCancel(): void {
  open.value = false;
  emit("cancel");
}
</script>

<template>
  <dialog ref="dialogRef" class="hd-dialog" @click.self="onCancel" @close="onCancel">
    <h2 class="hd-dialog__title">{{ props.title }}</h2>
    <p v-if="props.message" class="hd-dialog__message">{{ props.message }}</p>
    <slot />
    <div class="hd-dialog__actions">
      <HdButton v-if="props.cancelLabel" variant="secondary" data-testid="hd-dialog-cancel" @click="onCancel">
        {{ props.cancelLabel }}
      </HdButton>
      <HdButton
        :variant="props.variant === 'danger' ? 'primary' : 'success'"
        data-testid="hd-dialog-confirm"
        @click="onConfirm"
      >
        {{ props.confirmLabel }}
      </HdButton>
    </div>
  </dialog>
</template>

<style scoped>
.hd-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-card);
  padding: 24px;
  margin: 0;
  max-width: 420px;
  width: calc(100% - 32px);
}
.hd-dialog::backdrop {
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}
.hd-dialog__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0 0 8px;
}
.hd-dialog__message {
  font-family: var(--font-body);
  font-size: var(--text-body-md);
  margin: 0 0 20px;
  color: var(--color-ink-muted);
}
.hd-dialog__actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>
