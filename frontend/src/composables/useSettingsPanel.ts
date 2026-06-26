import { ref } from "vue";

const isOpen = ref(false);
const focusNameOnOpen = ref(false);

export function useSettingsPanel() {
  function open(): void {
    focusNameOnOpen.value = false;
    isOpen.value = true;
  }

  function openForName(): void {
    focusNameOnOpen.value = true;
    isOpen.value = true;
  }

  function close(): void {
    isOpen.value = false;
    focusNameOnOpen.value = false;
  }

  return { isOpen, focusNameOnOpen, open, openForName, close };
}
