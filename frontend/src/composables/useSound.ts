import { customRef } from "vue";

export const SOUND_KEYS = {
  roundStart: "/sounds/round-start.ogg",
  tick: "/sounds/tick.ogg",
  reveal: "/sounds/reveal.ogg",
  winner: "/sounds/winner.ogg",
  click: "/sounds/click.ogg",
} as const;

export type SoundKey = keyof typeof SOUND_KEYS;

const STORAGE_KEY = "ds:sound-enabled";

function readEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "true";
  } catch {
    return false;
  }
}

function writeEnabled(v: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, v ? "true" : "false");
  } catch {
    /* localStorage unavailable */
  }
}

// enabled is a module-level singleton: initial value is read from localStorage
// ONCE at module load. Tests that need a pre-seeded value must vi.resetModules()
// and re-import, not just write to localStorage before import.
const enabled = customRef<boolean>((track, trigger) => {
  let value = readEnabled();
  return {
    get() {
      track();
      return value;
    },
    set(newValue: boolean) {
      value = newValue;
      writeEnabled(newValue);
      trigger();
    },
  };
});

const cache = new Map<SoundKey, HTMLAudioElement>();

function getAudio(key: SoundKey): HTMLAudioElement {
  let audio = cache.get(key);
  if (!audio) {
    audio = new Audio(SOUND_KEYS[key]);
    audio.volume = 0.5;
    cache.set(key, audio);
  }
  return audio;
}

export function useSound() {
  function play(key: SoundKey): void {
    if (!enabled.value) return;
    const audio = getAudio(key);
    audio.currentTime = 0;
    void audio.play().catch(() => {
      /* autoplay blocked or unsupported */
    });
  }

  return { enabled, play };
}
