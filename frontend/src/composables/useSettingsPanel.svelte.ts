let isOpen = $state(false);
let focusNameOnOpen = $state(false);
// Action to resume once the player has picked a name (e.g. the Create Room
// click that triggered the name prompt). SettingsPanel runs it on close.
let pendingNameAction = $state<(() => void) | null>(null);

export function useSettingsPanel() {
  function open(): void {
    focusNameOnOpen = false;
    pendingNameAction = null;
    isOpen = true;
  }

  function openForName(action?: () => void): void {
    focusNameOnOpen = true;
    pendingNameAction = action ?? null;
    isOpen = true;
  }

  function close(): void {
    isOpen = false;
    focusNameOnOpen = false;
    pendingNameAction = null;
  }

  return {
    get isOpen() {
      return isOpen;
    },
    set isOpen(value) {
      isOpen = value;
    },
    get focusNameOnOpen() {
      return focusNameOnOpen;
    },
    set focusNameOnOpen(value) {
      focusNameOnOpen = value;
    },
    get pendingNameAction() {
      return pendingNameAction;
    },
    set pendingNameAction(value) {
      pendingNameAction = value;
    },
    open,
    openForName,
    close,
  };
}
