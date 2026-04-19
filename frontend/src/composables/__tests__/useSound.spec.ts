import { beforeEach, describe, expect, it, vi } from "vitest";

const playMock = vi.fn();
const muteMock = vi.fn();

vi.mock("howler", () => ({
  Howl: vi.fn().mockImplementation(() => ({
    play: playMock,
    mute: muteMock,
  })),
}));

import { SOUND_KEYS, useSound } from "@/composables/useSound";

describe("useSound", () => {
  beforeEach(() => {
    playMock.mockClear();
    muteMock.mockClear();
    localStorage.clear();
  });

  it("exposes the expected sound keys", () => {
    expect(Object.keys(SOUND_KEYS)).toEqual(["roundStart", "tick", "reveal", "winner", "click"]);
  });

  it("is disabled by default and does not call play", () => {
    const { enabled, play } = useSound();
    expect(enabled.value).toBe(false);
    play("click");
    expect(playMock).not.toHaveBeenCalled();
  });

  it("plays when enabled is set to true", () => {
    const { enabled, play } = useSound();
    enabled.value = true;
    play("click");
    expect(playMock).toHaveBeenCalledTimes(1);
  });

  it("persists the enabled flag to localStorage", () => {
    const { enabled } = useSound();
    enabled.value = true;
    expect(localStorage.getItem("ds:sound-enabled")).toBe("true");

    const second = useSound();
    expect(second.enabled.value).toBe(true);
  });
});
