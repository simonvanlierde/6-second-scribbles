<script setup lang="ts">
import { ref, useId, watch } from "vue";

import HdButton from "@/components/ui/HdButton.vue";
import HdIconButton from "@/components/ui/HdIconButton.vue";

interface Props {
  title: string;
  message?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "primary" | "danger";
  /** Shows a close button next to the title, which cancels like Escape does. */
  closeLabel?: string;
  /** Set false for a dialog closed only by its close button. */
  actions?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  message: "",
  confirmLabel: "Confirm",
  variant: "danger",
  actions: true,
  // cancelLabel intentionally has no default
});

const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ confirm: []; cancel: [] }>();

const dialogRef = ref<HTMLDialogElement | null>(null);
const titleId = useId();
const messageId = useId();

// Native <dialog> fires a `close` event on ANY close, including our own
// el.close(). Without this flag a programmatic close (confirm/backdrop) would
// re-enter onClose and emit a spurious `cancel` alongside the real event.
let programmaticClose = false;

watch(
  open,
  (isOpen) => {
    const el = dialogRef.value;
    if (!el) return;
    if (isOpen && !el.open) el.showModal();
    else if (!isOpen && el.open) {
      programmaticClose = true;
      el.close();
    }
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

// Only user-initiated closes (Esc key) should count as a cancel; the close
// event from our own el.close() is swallowed via the programmaticClose flag.
function onClose(): void {
  if (programmaticClose) {
    programmaticClose = false;
    return;
  }
  onCancel();
}
</script>

<template>
  <!-- biome-ignore lint/a11y/useKeyWithClickEvents: keyboard users cancel via Escape, handled by @close -->
  <dialog
    ref="dialogRef"
    class="hd-dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="props.message ? messageId : undefined"
    @click.self="onCancel"
    @close="onClose"
  >
    <div class="hd-dialog__header">
      <h2 :id="titleId" class="hd-dialog__title">{{ props.title }}</h2>
      <HdIconButton
        v-if="props.closeLabel"
        :label="props.closeLabel"
        variant="ghost"
        data-testid="hd-dialog-close"
        @click="onCancel"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </HdIconButton>
    </div>
    <p v-if="props.message" :id="messageId" class="hd-dialog__message">{{ props.message }}</p>
    <slot />
    <div v-if="props.actions" class="hd-dialog__actions">
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
.hd-dialog__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.hd-dialog__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
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
