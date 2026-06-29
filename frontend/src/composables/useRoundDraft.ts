import { onMounted, onUnmounted } from "vue";

interface RoundDraftOptions<T> {
  /** The round the draft belongs to; a restore only applies when this matches. */
  round: () => number;
  /** Build the payload to persist. */
  collect: () => T;
  /** Apply a restored payload back into component state. */
  apply: (data: T) => void;
  /** Whether persisting is still meaningful (e.g. not yet submitted). */
  active: () => boolean;
}

/**
 * Round-gated localStorage draft for in-progress client state (drawing strokes,
 * typed guesses) that the server doesn't hold until submit. Persists on
 * `pagehide`/unmount — `pagehide` fires on refresh/navigation where `onUnmounted`
 * does not — and only restores a draft saved for the current round.
 *
 * The caller invokes `restore()` itself (so it can order it relative to other
 * setup, e.g. after a canvas is initialised) and `clear()` on submit.
 */
export function useRoundDraft<T>(key: string, options: RoundDraftOptions<T>) {
  function persist() {
    if (!options.active()) return;
    try {
      localStorage.setItem(key, JSON.stringify({ round: options.round(), data: options.collect() }));
    } catch {
      /* localStorage unavailable */
    }
  }

  function restore(): boolean {
    try {
      const saved = localStorage.getItem(key);
      if (!saved) return false;
      const parsed = JSON.parse(saved) as { round?: number; data?: T };
      if (parsed.round !== options.round() || parsed.data === undefined) {
        localStorage.removeItem(key);
        return false;
      }
      options.apply(parsed.data);
      return true;
    } catch {
      clear();
      return false;
    }
  }

  function clear() {
    try {
      localStorage.removeItem(key);
    } catch {
      /* localStorage unavailable */
    }
  }

  onMounted(() => window.addEventListener("pagehide", persist));
  onUnmounted(() => {
    window.removeEventListener("pagehide", persist);
    persist();
  });

  return { restore, clear };
}
