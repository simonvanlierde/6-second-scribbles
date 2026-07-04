import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { GAME_SETTINGS } from "@/config/gameConfig";
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
    expect(store.playersList[0]).toMatchObject({
      id: "p1",
      name: "Alice",
      score: 0,
    });
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

// Persistence of localPlayerName is handled by pinia-plugin-persistedstate (key: "gameState").
// Testing the plugin itself is out of scope; it is covered by the library's own test suite.

describe("player locale state", () => {
  it("tracks the local player locale separately", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.addPlayer("p1", "Alice");

    store.setLocalPlayerLocale("fr");

    expect(store.localPlayerLocale).toBe("fr");
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
    store.startGame("hard", 8, 90, 60);
    expect(store.playersList.every((p) => p.score === 0)).toBe(true);
    expect(store.currentRound).toBe(0);
    expect(store.difficulty).toBe("hard");
    expect(store.maxRounds).toBe(8);
    expect(store.drawingTimeLimit).toBe(90);
    expect(store.guessingTimeLimit).toBe(60);
  });
});

describe("startRound", () => {
  it("sets phase to drawing and clears strokes", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.setReadyStatus(2, 2);
    store.setPlayerDrawing("p1", "data:image/png;base64,old");
    store.applyPartialStroke("p1", { color: "#000", width: 2, points: [{ x: 0, y: 0 }] }, true);
    store.startRound(1, { p1: { category: "Animals", items: ["cat", "dog"] } });
    expect(store.gamePhase).toBe("drawing");
    expect(store.currentStrokes).toHaveLength(0);
    expect(store.currentRound).toBe(1);
    expect(store.readyCount).toBe(0);
    expect(store.totalPlayers).toBe(2);
    expect(store.playersList[0]?.drawing).toBeUndefined();
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

describe("startGuessing", () => {
  it("resets ready status and stores the server start time", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.setReadyStatus(2, 2);

    store.startGuessing(12345, { p1: "p2", p2: "p1" });

    expect(store.gamePhase).toBe("guessing");
    expect(store.guessingStartTime).toBe(12345);
    expect(store.guessTargets).toEqual({ p1: "p2", p2: "p1" });
    expect(store.readyCount).toBe(0);
    expect(store.totalPlayers).toBe(2);
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
  it("sets phase to final results and resets ready status", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.setReadyStatus(2, 2);
    store.endGame();
    expect(store.gamePhase).toBe("final_results");
    expect(store.readyCount).toBe(0);
    expect(store.totalPlayers).toBe(2);
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
// Drawing history (end-of-game gallery)
// ---------------------------------------------------------------------------

describe("captureRoundDrawings", () => {
  it("snapshots one entry per player that submitted a drawing", () => {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Alice" },
      { id: "p2", name: "Bob" },
      { id: "p3", name: "Carol" },
    ]);
    store.setPlayerDrawing("p1", "data:image/png;base64,AAA");
    store.setPlayerDrawing("p2", "data:image/png;base64,BBB");
    // p3 never drew.

    store.captureRoundDrawings(1);

    expect(store.drawingHistory).toHaveLength(2);
    expect(store.drawingHistory.map((d) => d.playerId)).toEqual(["p1", "p2"]);
    expect(store.drawingHistory[0]).toMatchObject({ round: 1, name: "Alice", drawing: "data:image/png;base64,AAA" });
    expect(store.drawingHistory[0]?.color).toBeTruthy();
  });

  it("accumulates across rounds with the correct round number", () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Alice" }]);
    store.setPlayerDrawing("p1", "data:image/png;base64,R1");
    store.captureRoundDrawings(1);
    store.setPlayerDrawing("p1", "data:image/png;base64,R2");
    store.captureRoundDrawings(2);

    expect(store.drawingHistory.map((d) => d.round)).toEqual([1, 2]);
    expect(store.drawingHistory.map((d) => d.drawing)).toEqual([
      "data:image/png;base64,R1",
      "data:image/png;base64,R2",
    ]);
  });

  it("folds the round's correct guesses into totalGuessesMade", () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Alice" }]);
    store.setRoundResults([
      { playerId: "p1", targetPlayerId: "p2", correctGuesses: 3, totalItems: 5, pointsEarned: 30 },
      { playerId: "p2", targetPlayerId: "p1", correctGuesses: 2, totalItems: 5, pointsEarned: 20 },
    ]);
    store.captureRoundDrawings(1);

    expect(store.totalGuessesMade).toBe(5);
  });

  it("is cleared by resetRound and reset", () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Alice" }]);
    store.setPlayerDrawing("p1", "data:image/png;base64,AAA");
    store.setRoundResults([
      { playerId: "p1", targetPlayerId: "p2", correctGuesses: 1, totalItems: 2, pointsEarned: 10 },
    ]);
    store.captureRoundDrawings(1);

    store.resetRound();
    expect(store.drawingHistory).toHaveLength(0);
    expect(store.totalGuessesMade).toBe(0);

    store.setPlayerDrawing("p1", "data:image/png;base64,BBB");
    store.captureRoundDrawings(2);
    store.reset();
    expect(store.drawingHistory).toHaveLength(0);
    expect(store.totalGuessesMade).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Kick votes
// ---------------------------------------------------------------------------

describe("kick votes", () => {
  it("startKickVote adds a vote entry", () => {
    const store = useGameStore();
    const vote = {
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: Date.now() + 30_000,
    };
    store.startKickVote("p2", vote);
    expect(store.kickVotes.get("p2")).toEqual(vote);
  });

  it("updateKickVote updates an existing vote", () => {
    const store = useGameStore();
    store.startKickVote("p2", {
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 0,
    });
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
    store.startKickVote("p2", {
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 0,
    });
    store.removeKickVote("p2");
    expect(store.kickVotes.has("p2")).toBe(false);
  });

  it("removeKickVote is a no-op for unknown target", () => {
    const store = useGameStore();
    store.startKickVote("p2", {
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 0,
    });
    store.removeKickVote("ghost");
    expect(store.kickVotes.size).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// applyPartialStroke()
// ---------------------------------------------------------------------------

describe("applyPartialStroke", () => {
  it("appends delta fragments to the same stroke and starts a new one on strokeStart", () => {
    const store = useGameStore();
    store.applyPartialStroke("p1", { color: "#000", width: 2, points: [{ x: 0, y: 0 }] }, true);
    store.applyPartialStroke("p1", { color: "#000", width: 2, points: [{ x: 1, y: 1 }] }, false);
    // One stroke, points appended (no per-fragment stroke growth).
    expect(store.currentStrokes).toHaveLength(1);
    expect(store.currentStrokes[0]?.points).toHaveLength(2);

    store.applyPartialStroke("p1", { color: "#000", width: 2, points: [{ x: 2, y: 2 }] }, true);
    expect(store.currentStrokes).toHaveLength(2);
  });

  it("keeps each player's in-progress stroke separate", () => {
    const store = useGameStore();
    store.applyPartialStroke("p1", { color: "#000", width: 2, points: [{ x: 0, y: 0 }] }, true);
    store.applyPartialStroke("p2", { color: "#f00", width: 3, points: [{ x: 5, y: 5 }] }, true);
    store.applyPartialStroke("p1", { color: "#000", width: 2, points: [{ x: 1, y: 1 }] }, false);
    expect(store.currentStrokes).toHaveLength(2);
    expect(store.currentStrokes[0]?.points).toHaveLength(2);
    expect(store.currentStrokes[1]?.points).toHaveLength(1);
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
    store.applyPartialStroke("p1", { color: "#f00", width: 3, points: [] }, true);
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

describe("player presence", () => {
  it("defaults players to connected and keeps a disconnected player in the roster", () => {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Alice" },
      { id: "p2", name: "Bob" },
    ]);
    expect(store.players.get("p1")?.connected).toBe(true);

    store.setPlayerConnected("p2", false);
    expect(store.players.get("p2")?.connected).toBe(false);
    expect(store.playersList).toHaveLength(2);

    store.setPlayerConnected("p2", true);
    expect(store.players.get("p2")?.connected).toBe(true);
  });

  it("preserves connection state across a setPlayers refresh that omits it", () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Alice" }]);
    store.setPlayerConnected("p1", false);

    store.setPlayers([{ id: "p1", name: "Alice" }]);
    expect(store.players.get("p1")?.connected).toBe(false);

    store.setPlayers([{ id: "p1", name: "Alice", connected: true }]);
    expect(store.players.get("p1")?.connected).toBe(true);
  });
});
