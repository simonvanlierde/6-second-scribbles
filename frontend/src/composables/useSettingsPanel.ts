import { ref } from "vue";

const isOpen = ref(false);
const focusNameOnOpen = ref(false);
// Action to resume once the player has picked a name (e.g. the Create Room
// click that triggered the name prompt). SettingsPanel runs it on close.
const pendingNameAction = ref<(() => void) | null>(null);

export function useSettingsPanel() {
  function open(): void {
    focusNameOnOpen.value = false;
    pendingNameAction.value = null;
    isOpen.value = true;
  }

  function openForName(action?: () => void): void {
    focusNameOnOpen.value = true;
    pendingNameAction.value = action ?? null;
    isOpen.value = true;
  }

  function close(): void {
    isOpen.value = false;
    focusNameOnOpen.value = false;
    pendingNameAction.value = null;
  }

  return {
    isOpen,
    focusNameOnOpen,
    pendingNameAction,
    open,
    openForName,
    close,
  };
}
