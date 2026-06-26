import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGameConnection } from "@/composables/useGameConnection";
import { useGameStore } from "@/stores/game";

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;

  readyState = MockWebSocket.OPEN;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send(payload: string) {
    this.sent.push(payload);
  }

  close() {}
}

describe("client message handlers", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
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
    store.setLocalPadVisible(true);
    const { handleMessage } = useGameConnection();

    handleMessage({ type: "pad_visibility", visible: false });
    expect(store.roomPadVisible).toBe(false);
    expect(store.localPadVisible).toBe(true);
  });

  it("applies settings_update to the store", () => {
    const store = useGameStore();
    store.localPlayerId = "p2";
    store.localPlayerName = "Player";
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "settings_update",
      difficulty: "hard",
      rounds: 8,
      drawingTimeLimit: 75,
      guessingTimeLimit: 60,
    });

    expect(store.difficulty).toBe("hard");
    expect(store.maxRounds).toBe(8);
    expect(store.drawingTimeLimit).toBe(75);
    expect(store.guessingTimeLimit).toBe(60);
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
      roundStartTime: null,
      guessingStartTime: null,
      drawingTimeLimit: null,
      guessingTimeLimit: 60,
      guessTargets: {},
      padVisibility: true,
      isPrivate: true,
      defaultLocale: "en",
    });

    expect(store.playersList.map((player) => player.id)).toEqual(["p1", "p2"]);
    expect(store.hostId).toBe("p1");
    expect(store.isPrivateRoom).toBe(true);
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
      isHost: false,
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
      reason: "kicked",
    });

    expect(store.playersList.map((player) => player.id)).toEqual(["p1"]);
  });

  it("start_round sets round, phase, and local player card", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.localPlayerId = "p1";
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "start_round",
      round: 2,
      roundStartTime: 1000,
      cards: {
        p1: { category: "Animals", items: ["cat"], alternatives: null },
      },
    });

    expect(store.currentRound).toBe(2);
    expect(store.gamePhase).toBe("drawing");
    expect(store.localPlayerCard).toEqual({
      category: "Animals",
      items: ["cat"],
      alternatives: null,
    });
    expect(store.roundStartTime).toBe(1000);
  });

  it("round_complete updates scores and sets round results phase", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "round_complete",
      results: [
        {
          playerId: "p1",
          targetPlayerId: "p2",
          correctGuesses: 2,
          totalItems: 3,
          pointsEarned: 10,
        },
      ],
      scores: { p1: 10, p2: 0 },
    });

    expect(store.gamePhase).toBe("round_results");
    expect(store.playersList.find((p) => p.id === "p1")?.score).toBe(10);
    expect(store.lastRoundResults).toHaveLength(1);
  });

  it("game_complete ends the game and updates final scores", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "game_complete",
      finalScores: { p1: 30, p2: 20 },
      winner: "p1",
    });

    expect(store.gamePhase).toBe("final_results");
    expect(store.playersList.find((p) => p.id === "p1")?.score).toBe(30);
  });

  it("host_changed updates hostId", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({ type: "host_changed", newHostId: "p2" });
    expect(store.hostId).toBe("p2");
  });

  it("player_left removes the player", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    const { handleMessage } = useGameConnection();

    handleMessage({ type: "player_left", playerId: "p2" });
    expect(store.playersList.map((p) => p.id)).toEqual(["p1"]);
  });

  it("kick_vote_started adds a kick vote entry", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "kick_vote_started",
      targetPlayerId: "p2",
      targetPlayerName: "Bob",
      initiatorId: "p1",
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 9999,
    });

    expect(store.kickVotes.get("p2")).toEqual({
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 9999,
    });
  });

  it("kick_vote_updated replaces the active kick vote state", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "kick_vote_started",
      targetPlayerId: "p2",
      targetPlayerName: "Bob",
      initiatorId: "p1",
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 9999,
    });

    handleMessage({
      type: "kick_vote_updated",
      targetPlayerId: "p2",
      currentVotes: 2,
      requiredVotes: 2,
    });

    expect(store.kickVotes.get("p2")).toEqual({
      currentVotes: 2,
      requiredVotes: 2,
      expiresAt: 9999,
    });
  });

  it("kick_vote_expired clears the active vote", () => {
    const store = useGameStore();
    const { handleMessage } = useGameConnection();

    handleMessage({
      type: "kick_vote_started",
      targetPlayerId: "p2",
      targetPlayerName: "Bob",
      initiatorId: "p1",
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: 9999,
    });

    handleMessage({ type: "kick_vote_expired", targetPlayerId: "p2" });
    expect(store.kickVotes.has("p2")).toBe(false);
  });

  it("validates outbound client events before sending them", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.localPlayerName = "Alice";
    const { connect, send } = useGameConnection();

    connect("ROOM01");
    MockWebSocket.instances[0]?.onopen?.();

    const socket = MockWebSocket.instances[0];
    expect(socket).toBeDefined();

    const sent = send({ type: "heartbeat" });
    expect(sent).toBe(true);
    expect(socket?.sent).toContain(JSON.stringify({ type: "heartbeat" }));

    const invalid = send({ type: "submit_guess", playerId: "p1" } as never);
    expect(invalid).toBe(false);
    expect(socket?.sent).not.toContain(JSON.stringify({ type: "submit_guess", playerId: "p1" }));
  });

  it("does not open a websocket for an empty room code", () => {
    const { connect } = useGameConnection();

    connect("");

    expect(MockWebSocket.instances).toHaveLength(0);
  });
});
