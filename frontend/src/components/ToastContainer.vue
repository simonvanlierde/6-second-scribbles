<script setup lang="ts">
import { useNotifications } from "@/composables/notifications";

const { notifications } = useNotifications();

const toastClasses: Record<string, string> = {
  info: "bg-black/75",
  success: "bg-success-dark",
  error: "bg-danger",
};
</script>

<template>
  <div class="fixed bottom-5 left-1/2 z-[3000] flex -translate-x-1/2 flex-col gap-2" aria-live="polite">
    <div
      v-for="n in notifications"
      :key="n.id"
      class="rounded-sm px-4 py-2 text-[0.95rem] text-white"
      :class="toastClasses[n.type]"
    >
      {{ n.text }}
    </div>
  </div>
</template>
