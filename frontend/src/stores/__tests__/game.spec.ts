import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { GAME_SETTINGS, STORAGE_KEYS } from "@/config/gameConfig";
import { useGameStore } from "@/stores/game";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();

  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.get(key) ?? null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(key, value);
    },
  };
}

beforeEach(() => {
  Object.defineProperty(globalThis, "localStorage", {
    value: createMemoryStorage(),
    configurable: true,
    writable: true,
  });
  setActivePinia(createPinia());
});

// ---------------------------------------------------------------------------
// Player management
// ---------------------------------------------------------------------------

describe("addPlayer", () => {
  it("adds a new player with score 0", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    expect(store.playersList).toHaveLength(1);
    expect(store.playersList[0]).toMatchObject({ id: "p1", name: "Alice", score: 0 });
  });

  it("ignores duplicate player ids", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p1", "Alice 2");
    expect(store.playersList).toHaveLength(1);
  });

  it("sets hostId to first player when no host is set", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    expect(store.hostId).toBe("p1");
  });

  it("does not override an existing host", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    expect(store.hostId).toBe("p1");
  });
});

describe("removePlayer", () => {
  it("removes an existing player", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.removePlayer("p1");
    expect(store.playersList.map((p) => p.id)).toEqual(["p2"]);
  });

  it("is a no-op for unknown player id", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.removePlayer("ghost");
    expect(store.playersList).toHaveLength(1);
  });
});

describe("setPlayers", () => {
  it("replaces the entire player map", () => {
    const store = useGameStore();
    store.addPlayer("stale", "Stale");
    store.setPlayers([
      { id: "p1", name: "Alice" },
      { id: "p2", name: "Bob" },
    ]);
    expect(store.playersList.map((p) => p.id)).toEqual(["p1", "p2"]);
  });

  it("preserves scores for existing players", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.updateScores({ p1: 42 });
    store.setPlayers([{ id: "p1", name: "Alice" }]);
    expect(store.playersList[0]?.score).toBe(42);
  });

  it("initialises new players with score 0", () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p2", name: "Bob" }]);
    expect(store.playersList[0]?.score).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Computed properties
// ---------------------------------------------------------------------------

describe("canStartGame", () => {
  it("is false with fewer than 2 players", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    expect(store.canStartGame).toBe(false);
  });

  it("is true with 2+ players in lobby phase", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    expect(store.canStartGame).toBe(true);
  });

  it("is false when not in lobby phase", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.gamePhase = "drawing";
    expect(store.canStartGame).toBe(false);
  });
});

describe("isHost", () => {
  it("is true when localPlayerId matches hostId", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.hostId = "p1";
    expect(store.isHost).toBe(true);
  });

  it("is false when localPlayerId does not match hostId", () => {
    const store = useGameStore();
    store.localPlayerId = "p2";
    store.hostId = "p1";
    expect(store.isHost).toBe(false);
  });
});

describe("localPlayer", () => {
  it("returns the player matching localPlayerId", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.localPlayerId = "p1";
    expect(store.localPlayer?.name).toBe("Alice");
  });

  it("returns undefined when localPlayerId has no matching player", () => {
    const store = useGameStore();
    store.localPlayerId = "ghost";
    expect(store.localPlayer).toBeUndefined();
  });
});

describe("player name persistence", () => {
  it("hydrates the local player name from localStorage", () => {
    localStorage.setItem(STORAGE_KEYS.PLAYER_NAME, "Persistent Player");

    const store = useGameStore();

    expect(store.localPlayerName).toBe("Persistent Player");
  });

  it("persists the local player name when it changes", async () => {
    const store = useGameStore();

    store.localPlayerName = "Persistent Player";
    await nextTick();

    expect(localStorage.getItem(STORAGE_KEYS.PLAYER_NAME)).toBe("Persistent Player");
  });
});

// ---------------------------------------------------------------------------
// Game flow actions
// ---------------------------------------------------------------------------

describe("startGame", () => {
  it("resets scores and round counter", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.updateScores({ p1: 10, p2: 5 });
    store.startGame("hard", 8, 90);
    expect(store.playersList.every((p) => p.score === 0)).toBe(true);
    expect(store.currentRound).toBe(0);
    expect(store.difficulty).toBe("hard");
    expect(store.maxRounds).toBe(8);
    expect(store.roundLength).toBe(90);
  });
});

describe("startRound", () => {
  it("sets phase to drawing and clears strokes", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addStroke({ color: "#000", width: 2, points: [{ x: 0, y: 0 }] });
    store.startRound(1, { p1: { category: "Animals", items: ["cat", "dog"] } });
    expect(store.gamePhase).toBe("drawing");
    expect(store.currentStrokes).toHaveLength(0);
    expect(store.currentRound).toBe(1);
  });

  it("assigns the local player card", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.localPlayerId = "p1";
    const card = { category: "Animals", items: ["dog", "cat"] };
    store.startRound(1, { p1: card });
    expect(store.localPlayerCard).toEqual(card);
  });
});

describe("resetRound", () => {
  it("resets round counter and all scores to 0", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.updateScores({ p1: 99 });
    store.currentRound = 3;
    store.resetRound();
    expect(store.currentRound).toBe(0);
    expect(store.playersList[0]?.score).toBe(0);
  });
});

describe("endGame", () => {
  it("sets phase to complete", () => {
    const store = useGameStore();
    store.endGame();
    expect(store.gamePhase).toBe("complete");
  });
});

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

describe("getFinalScores", () => {
  it("returns players sorted by score descending", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.addPlayer("p3", "Carol");
    store.updateScores({ p1: 10, p2: 30, p3: 20 });
    const scores = store.getFinalScores();
    expect(scores.map((s) => s.playerId)).toEqual(["p2", "p3", "p1"]);
  });
});

describe("getWinner", () => {
  it("returns the player with the highest score", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.updateScores({ p1: 5, p2: 15 });
    expect(store.getWinner()?.playerId).toBe("p2");
  });
});

// ---------------------------------------------------------------------------
// Kick votes
// ---------------------------------------------------------------------------

describe("kick votes", () => {
  it("startKickVote adds a vote entry", () => {
    const store = useGameStore();
    const vote = { currentVotes: 1, requiredVotes: 2, expiresAt: Date.now() + 30_000 };
    store.startKickVote("p2", vote);
    expect(store.kickVotes.get("p2")).toEqual(vote);
  });

  it("updateKickVote updates an existing vote", () => {
    const store = useGameStore();
    store.startKickVote("p2", { currentVotes: 1, requiredVotes: 2, expiresAt: 0 });
    store.updateKickVote("p2", { currentVotes: 2, requiredVotes: 2 });
    expect(store.kickVotes.get("p2")?.currentVotes).toBe(2);
  });

  it("updateKickVote is a no-op for unknown target", () => {
    const store = useGameStore();
    store.updateKickVote("ghost", { currentVotes: 1, requiredVotes: 2 });
    expect(store.kickVotes.size).toBe(0);
  });

  it("removeKickVote deletes the entry", () => {
    const store = useGameStore();
    store.startKickVote("p2", { currentVotes: 1, requiredVotes: 2, expiresAt: 0 });
    store.removeKickVote("p2");
    expect(store.kickVotes.has("p2")).toBe(false);
  });

  it("removeKickVote is a no-op for unknown target", () => {
    const store = useGameStore();
    store.startKickVote("p2", { currentVotes: 1, requiredVotes: 2, expiresAt: 0 });
    store.removeKickVote("ghost");
    expect(store.kickVotes.size).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// reset()
// ---------------------------------------------------------------------------

describe("reset", () => {
  it("restores all state to defaults", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.gamePhase = "drawing";
    store.hostId = "p1";
    store.setRoomCode("ABCDEF");
    store.addStroke({ color: "#f00", width: 3, points: [] });
    store.reset();

    expect(store.playersList).toHaveLength(0);
    expect(store.gamePhase).toBe("lobby");
    expect(store.hostId).toBeNull();
    expect(store.roomCode).toBe("");
    expect(store.currentStrokes).toHaveLength(0);
    expect(store.currentRound).toBe(0);
    expect(store.maxRounds).toBe(GAME_SETTINGS.rounds.DEFAULT);
    expect(store.difficulty).toBe(GAME_SETTINGS.difficulty.DEFAULT);
  });
});
