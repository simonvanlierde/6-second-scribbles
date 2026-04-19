<script setup lang="ts">
import { ref, watch } from "vue";

import HdIconButton from "@/components/ui/HdIconButton.vue";

interface Props {
  title: string;
  side?: "right" | "bottom";
}

const props = withDefaults(defineProps<Props>(), { side: "right" });

const open = defineModel<boolean>("open", { default: false });
const emit = defineEmits<{ close: [] }>();

const dialogRef = ref<HTMLDialogElement | null>(null);

watch(
  open,
  (v) => {
    const el = dialogRef.value;
    if (!el) return;
    if (v && !el.open) el.showModal();
    else if (!v && el.open) el.close();
  },
  { flush: "post" },
);

function onClose(): void {
  open.value = false;
  emit("close");
}

function onBackdropClick(e: MouseEvent): void {
  if (e.target === dialogRef.value) onClose();
}
</script>

<template>
  <dialog
    ref="dialogRef"
    class="hd-sidepanel"
    :class="`hd-sidepanel--${props.side}`"
    @click="onBackdropClick"
    @close="onClose"
  >
    <header class="hd-sidepanel__header">
      <h2 class="hd-sidepanel__title">{{ props.title }}</h2>
      <HdIconButton label="Close" variant="ghost" data-testid="hd-sidepanel-close" @click="onClose">
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
    </header>
    <div class="hd-sidepanel__body"><slot /></div>
  </dialog>
</template>

<style scoped>
.hd-sidepanel {
  background: var(--color-card);
  color: var(--color-ink);
  border: 2.5px solid var(--color-ink);
  box-shadow: var(--shadow-card);
  margin: 0;
  padding: 0;
  max-width: 100vw;
  max-height: 100vh;
}
.hd-sidepanel::backdrop {
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(2px);
}
.hd-sidepanel--right {
  position: fixed;
  right: 0;
  top: 0;
  height: 100vh;
  width: min(360px, 100vw);
  border-radius: 18px 0 0 22px;
}
.hd-sidepanel--bottom {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  top: auto;
  width: 100vw;
  max-height: 85vh;
  border-radius: 22px 22px 0 0;
}
.hd-sidepanel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1.5px dashed var(--color-ink);
}
.hd-sidepanel__title {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: var(--text-heading-md);
  margin: 0;
}
.hd-sidepanel__body {
  padding: 20px;
  overflow-y: auto;
}
@media (max-width: 640px) {
  .hd-sidepanel--right {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    top: auto;
    width: 100vw;
    height: auto;
    max-height: 85vh;
    border-radius: 22px 22px 0 0;
  }
}
</style>
