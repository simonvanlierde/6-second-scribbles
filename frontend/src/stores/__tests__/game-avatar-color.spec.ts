import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { AVATAR_COLORS, getAvatarColor } from "@/composables/useAvatar";
import { useGameStore } from "@/stores/game";

describe("game store — localPlayerColor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("assigns a deterministic color after setLocalPlayer if none is set", () => {
    const store = useGameStore();
    // Force-clear the default so setLocalPlayer's guard derives a new colour.
    store.setLocalPlayerColor(AVATAR_COLORS[0]);
    store.localPlayerColor = "" as never;
    store.setLocalPlayer("player-abc", "Simon");
    expect(store.localPlayerColor).toBe(getAvatarColor("player-abc"));
  });

  it("setLocalPlayerColor accepts a valid AvatarColor", () => {
    const store = useGameStore();
    store.setLocalPlayerColor(AVATAR_COLORS[2]);
    expect(store.localPlayerColor).toBe(AVATAR_COLORS[2]);
  });

  it("setLocalPlayerColor ignores invalid colors", () => {
    const store = useGameStore();
    const before = store.localPlayerColor;
    store.setLocalPlayerColor("bogus" as never);
    expect(store.localPlayerColor).toBe(before);
  });
});
