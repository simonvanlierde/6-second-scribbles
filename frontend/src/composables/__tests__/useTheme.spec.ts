import { beforeEach, describe, expect, it, vi } from "vitest";

describe("useTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
    vi.resetModules();
  });

  it("defaults to auto and removes data-theme from <html>", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    expect(theme.value).toBe("auto");
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
  });

  it("persists light / dark to localStorage and sets data-theme", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    theme.value = "light";
    expect(localStorage.getItem("ds:theme")).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    theme.value = "dark";
    expect(localStorage.getItem("ds:theme")).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("clears data-theme when switched back to auto", async () => {
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    theme.value = "dark";
    theme.value = "auto";
    expect(document.documentElement.hasAttribute("data-theme")).toBe(false);
    expect(localStorage.getItem("ds:theme")).toBe("auto");
  });

  it("restores from localStorage on module reload", async () => {
    localStorage.setItem("ds:theme", "dark");
    const { useTheme } = await import("@/composables/useTheme");
    const { theme } = useTheme();
    expect(theme.value).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
