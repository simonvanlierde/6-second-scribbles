import { tick } from "svelte";

// One shared polite live region (rendered in App.svelte) for screen-reader news
// that has no visible text change of its own: phase changes, time running low.
let message = $state("");

export function useAnnouncer() {
  function announce(text: string): void {
    // Clear first, so the same text twice in a row is still read out.
    message = "";
    void tick().then(() => {
      message = text;
    });
  }

  return {
    get message() {
      return message;
    },
    set message(value: string) {
      message = value;
    },
    announce,
  };
}
