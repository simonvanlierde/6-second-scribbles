import { nextTick, ref } from "vue";

// One shared polite live region (rendered in App.vue) for screen-reader news
// that has no visible text change of its own: phase changes, time running low.
const message = ref("");

export function useAnnouncer() {
  function announce(text: string): void {
    // Clear first, so the same text twice in a row is still read out.
    message.value = "";
    void nextTick(() => {
      message.value = text;
    });
  }

  return { message, announce };
}
