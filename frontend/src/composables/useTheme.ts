import { customRef } from "vue";

export type Theme = "light" | "dark" | "auto";

const STORAGE_KEY = "ds:theme";

function readTheme(): Theme {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark" || v === "auto") return v;
  } catch {
    /* localStorage unavailable */
  }
  return "auto";
}

function writeTheme(v: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, v);
  } catch {
    /* localStorage unavailable */
  }
}

function applyTheme(v: Theme): void {
  if (typeof document === "undefined") return;
  if (v === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", v);
}

// theme is a module-level singleton: initial value is read from localStorage
// ONCE at module load. Tests that need a pre-seeded value must vi.resetModules()
// and re-import, not just write to localStorage before import.
const theme = customRef<Theme>((track, trigger) => {
  let value = readTheme();
  applyTheme(value);
  return {
    get() {
      track();
      return value;
    },
    set(next: Theme) {
      value = next;
      writeTheme(next);
      applyTheme(next);
      trigger();
    },
  };
});

export function useTheme() {
  return { theme };
}
