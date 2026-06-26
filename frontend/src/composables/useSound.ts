import { Howl } from "howler";
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

const cache = new Map<SoundKey, Howl>();

function getHowl(key: SoundKey): Howl {
  let h = cache.get(key);
  if (!h) {
    h = new Howl({
      src: [SOUND_KEYS[key]],
      volume: 0.5,
      preload: true,
    });
    cache.set(key, h);
  }
  return h;
}

export function useSound() {
  function play(key: SoundKey): void {
    if (!enabled.value) return;
    getHowl(key).play();
  }

  return { enabled, play };
}
