import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { AVATAR_COLORS, getAvatarColor } from "@/composables/useAvatar";
import { useGameStore } from "@/stores/game";

describe("game store — localPlayerColor", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
  });

  it("leaves the colour unpicked after setLocalPlayer, showing the room's or a per-id one", () => {
    const store = useGameStore();
    store.setLocalPlayer("player-abc", "Simon");
    expect(store.localPlayerColor).toBeNull();
    expect(store.localAvatarColor).toBe(getAvatarColor("player-abc"));

    store.setPlayers([{ id: "player-abc", name: "Simon", color: AVATAR_COLORS[4] }]);
    expect(store.localAvatarColor).toBe(AVATAR_COLORS[4]);
  });

  it("shows the colour the room assigned over a picked one the room gave to someone else", () => {
    const store = useGameStore();
    store.setLocalPlayer("player-abc", "Simon");
    store.setLocalPlayerColor(AVATAR_COLORS[2]);
    expect(store.localAvatarColor).toBe(AVATAR_COLORS[2]);

    store.setPlayers([{ id: "player-abc", name: "Simon", color: AVATAR_COLORS[4] }]);
    expect(store.localAvatarColor).toBe(AVATAR_COLORS[4]);
  });

  it("setPlayers keeps the server's colour and fills one for a player without", () => {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Ann", color: AVATAR_COLORS[1] },
      { id: "p2", name: "Bob", color: null },
    ]);
    expect(store.players.get("p1")?.color).toBe(AVATAR_COLORS[1]);
    expect(store.players.get("p2")?.color).toBe(getAvatarColor("p2"));
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
