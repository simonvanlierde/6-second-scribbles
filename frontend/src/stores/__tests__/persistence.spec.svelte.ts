import { flushSync } from "svelte";
import { beforeEach, describe, expect, it } from "vitest";

import { STORAGE_KEYS } from "@/config/gameConfig";

beforeEach(() => {
  localStorage.clear();
});

describe("game state persistence", () => {
  it("keeps identity and room preferences across reloads without restoring server-owned state", async () => {
    localStorage.setItem(
      STORAGE_KEYS.GAME_STATE,
      JSON.stringify({
        localPlayerId: "p1",
        localPlayerName: "Alice",
        localPlayerLocale: "nl",
        localPlayerColor: "var(--avatar-2)",
        roomCode: "ABC123",
        defaultLocale: "nl",
        localPadVisible: false,
        gamePhase: "drawing",
        currentRound: 3,
        hydrated: true,
      }),
    );
    const { useGameStore } = await import("@/stores/game.svelte");
    const store = useGameStore();
    expect(store.localPlayerId).toBe("p1");
    expect(store.localPlayerName).toBe("Alice");
    expect(store.localPlayerLocale).toBe("nl");
    expect(store.localPlayerColor).toBe("var(--avatar-2)");
    expect(store.roomCode).toBe("ABC123");
    expect(store.defaultLocale).toBe("nl");
    expect(store.localPadVisible).toBe(false);
    expect(store.gamePhase).toBe("lobby");
    expect(store.currentRound).toBe(0);
    expect(store.hydrated).toBe(false);

    store.setLocalPlayer("p2", "Robin");
    store.onStartRound({ round: 1, cards: {} });
    flushSync();
    expect(JSON.parse(localStorage.getItem(STORAGE_KEYS.GAME_STATE) ?? "{}")).toEqual({
      localPlayerId: "p2",
      localPlayerName: "Robin",
      localPlayerLocale: "nl",
      localPlayerColor: "var(--avatar-2)",
      roomCode: "ABC123",
      defaultLocale: "nl",
      localPadVisible: false,
    });
  });

  it("updates rendered player state when roster and scores change", async () => {
    const { useGameStore } = await import("@/stores/game.svelte");
    const store = useGameStore();
    let rendered = "";
    const dispose = $effect.root(() => {
      $effect(() => {
        rendered = store.playersList.map((player) => `${player.name}:${player.score}:${player.connected}`).join(",");
      });
    });
    try {
      store.addPlayer("p1", "Alice");
      flushSync();
      expect(rendered).toBe("Alice:0:true");
      store.onGameComplete({ finalScores: { p1: 12 } });
      store.setPlayerConnected("p1", false);
      flushSync();
      expect(rendered).toBe("Alice:12:false");
      store.removePlayer("p1");
      flushSync();
      expect(rendered).toBe("");
    } finally {
      dispose();
    }
  });
});
