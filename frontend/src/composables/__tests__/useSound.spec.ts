import { beforeEach, describe, expect, it, vi } from "vitest";

const playMock = vi.fn(() => Promise.resolve());

vi.stubGlobal(
  "Audio",
  vi.fn().mockImplementation(function (this: {
    play: typeof playMock;
    volume: number;
    currentTime: number;
  }) {
    this.play = playMock;
    this.volume = 0;
    this.currentTime = 0;
  }),
);

import { SOUND_KEYS, useSound } from "@/composables/useSound.svelte";

describe("useSound", () => {
  beforeEach(() => {
    playMock.mockClear();
    localStorage.clear();
  });

  it("exposes the expected sound keys", () => {
    expect(Object.keys(SOUND_KEYS)).toEqual(["roundStart", "tick", "reveal", "winner", "click"]);
  });

  it("is disabled by default and does not call play", () => {
    const sound = useSound();
    expect(sound.enabled).toBe(false);
    sound.play("click");
    expect(playMock).not.toHaveBeenCalled();
  });

  it("plays when enabled is set to true", () => {
    const sound = useSound();
    sound.enabled = true;
    sound.play("click");
    expect(playMock).toHaveBeenCalledTimes(1);
  });

  it("persists the enabled flag to localStorage across module reloads", async () => {
    const first = await import("@/composables/useSound.svelte");
    first.useSound().enabled = true;
    expect(localStorage.getItem("ds:sound-enabled")).toBe("true");

    vi.resetModules();
    const second = await import("@/composables/useSound.svelte");
    expect(second.useSound().enabled).toBe(true);
  });
});
