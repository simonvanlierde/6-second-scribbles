import { ref } from "vue";

// Module-level singleton: the global settings panel lives in App.vue and any
// view/composite can request it opens via useSettingsPanel().open().
const isOpen = ref(false);

export function useSettingsPanel() {
  function open(): void {
    isOpen.value = true;
  }

  function close(): void {
    isOpen.value = false;
  }

  return { isOpen, open, close };
}
