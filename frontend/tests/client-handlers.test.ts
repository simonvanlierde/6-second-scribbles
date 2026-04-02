import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useGameConnection } from "@/composables/useGameConnection";
import type { GameMessage } from "@/shared/types";
import { useGameStore } from "@/stores/game";

describe("client message handlers", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("applies draw_stroke to the store", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "draw_stroke",
      playerId: "p2",
      stroke: { color: "#000", width: 2, points: [{ x: 1, y: 2 }] },
    });

    expect(store.currentStrokes.length).toBeGreaterThan(0);
    expect(store.currentStrokes[0]?.color).toBe("#000");
  });

  it("adds remote partials but ignores local-origin partials", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "draw_stroke_partial",
      playerId: "p2",
      stroke: { color: "#123", width: 2, points: [{ x: 1, y: 2 }] },
    });
    expect(store.currentStrokes.length).toBeGreaterThan(0);

    const before = store.currentStrokes.length;
    handleMessage({
      type: "draw_stroke_partial",
      playerId: "p1",
      stroke: { color: "#123", width: 2, points: [{ x: 3, y: 4 }] },
    });
    expect(store.currentStrokes.length).toBe(before);
  });

  it("applies pad_visibility to the store", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({ type: "pad_visibility", playerId: "p1", visible: false });
    expect(store.showDrawpad).toBe(false);
  });

  it("applies settings_update to the store", () => {
    const store = useGameStore();
    store.localPlayerId = "p2";
    store.localPlayerName = "Player";
    const { handleMessage } = useGameConnection();

    const msg: GameMessage = { type: "settings_update", difficulty: "hard", rounds: 8, roundLength: 75 };
    handleMessage(msg);

    expect(store.difficulty).toBe("hard");
    expect(store.maxRounds).toBe(8);
    expect(store.roundLength).toBe(75);
  });

  it("replaces the player roster from room_state", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    store.addPlayer("stale-player", "Stale");

    handleMessage({
      type: "room_state",
      players: [
        { id: "p1", name: "Alice" },
        { id: "p2", name: "Bob" },
      ],
      hostId: "p1",
      categories: [],
      gamePhase: "lobby",
      difficulty: "medium",
      maxRounds: 5,
      padVisibility: true,
      language: "en",
    });

    expect(store.playersList.map((player) => player.id)).toEqual(["p1", "p2"]);
    expect(store.hostId).toBe("p1");
  });

  it("uses the authoritative player list from player_joined", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    store.addPlayer("p1", "Alice");
    store.addPlayer("ghost-player", "Ghost");

    handleMessage({
      type: "player_joined",
      playerId: "p2",
      name: "Bob",
      players: [
        { id: "p1", name: "Alice" },
        { id: "p2", name: "Bob" },
      ],
    });

    expect(store.playersList.map((player) => player.id)).toEqual(["p1", "p2"]);
  });

  it("removes kicked players from the roster", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");

    handleMessage({
      type: "player_kicked",
      playerId: "p2",
      playerName: "Bob",
    });

    expect(store.playersList.map((player) => player.id)).toEqual(["p1"]);
  });

  it("applies custom category add and remove broadcasts", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "custom_category_added",
      category: { name: "Animals" },
      items: ["cat", "dog"],
    });
    expect(store.categories).toEqual(["Animals"]);

    handleMessage({
      type: "custom_category_removed",
      category_id: 1,
      category_name: "Animals",
    });
    expect(store.categories).toEqual([]);
  });
});
