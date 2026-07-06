import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import {
  type HandlerContext,
  handleConnectionEvent,
  handleGameFlowEvent,
  handleKickEvent,
  handleResultsEvent,
} from "@/composables/connection/handlers";
import { useReactions } from "@/composables/useReactions";
import { useGameStore } from "@/stores/game";

describe("connection handlers translations", () => {
  let store: ReturnType<typeof useGameStore>;
  let showNotification: ReturnType<typeof vi.fn>;
  let ctx: HandlerContext;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useGameStore();
    showNotification = vi.fn();
    ctx = {
      store,
      router: { push: vi.fn() } as never,
      showNotification,
      send: vi.fn(),
      isObserverConnection: ref(false),
      stopStateRefresh: vi.fn(),
    };
  });

  it("uses translated host-changed and locale-update notifications", () => {
    store.setPlayers([
      { id: "p1", name: "Alice" },
      { id: "p2", name: "Bob" },
    ]);
    store.localPlayerId = "p1";

    handleConnectionEvent({ type: "host_changed", newHostId: "p2" }, ctx);
    handleGameFlowEvent({ type: "default_locale_update", locale: "fr" }, ctx);

    expect(showNotification).toHaveBeenNthCalledWith(1, "Bob is now the host");
    expect(showNotification).toHaveBeenNthCalledWith(2, "Room language changed to Français");
  });

  it("uses translated moderation notifications with interpolation", () => {
    store.localPlayerId = "p1";

    handleKickEvent(
      {
        type: "kick_vote_started",
        targetPlayerId: "p2",
        targetPlayerName: "Bob",
        initiatorId: "p1",
        currentVotes: 1,
        requiredVotes: 2,
        expiresAt: 12345,
      },
      ctx,
    );

    handleKickEvent(
      {
        type: "player_kicked",
        playerId: "p2",
        playerName: "Bob",
      },
      ctx,
    );

    expect(showNotification).toHaveBeenNthCalledWith(1, "Started kick vote for Bob");
    expect(showNotification).toHaveBeenNthCalledWith(2, "Bob was kicked from the room");
  });

  it("stores highlights and clears stale reactions on round_complete", () => {
    const reactions = useReactions();
    reactions.clear();
    reactions.add("p2", "laugh");

    handleGameFlowEvent(
      {
        type: "round_complete",
        results: [],
        scores: { p1: 0 },
        highlights: {
          bestGuesser: { playerId: "p1", detail: "2/2" },
          speedDemon: null,
          wildestMiss: null,
        },
      },
      ctx,
    );

    expect(store.lastHighlights?.bestGuesser?.playerId).toBe("p1");
    expect(reactions.countsFor("p2").laugh).toBe(0);
  });

  it("captures the round's drawings on round_complete, surviving the next start_round", () => {
    store.setPlayers([
      { id: "p1", name: "Alice" },
      { id: "p2", name: "Bob" },
    ]);
    store.localPlayerId = "p3"; // neither drawer is local, so drawings are accepted as-is
    store.currentRound = 1;
    store.setPlayerDrawing("p1", "data:image/png;base64,A1");
    store.setPlayerDrawing("p2", "data:image/png;base64,B1");

    handleGameFlowEvent(
      {
        type: "round_complete",
        results: [
          {
            playerId: "p1",
            targetPlayerId: "p2",
            correctGuesses: 2,
            totalItems: 3,
            pointsEarned: 20,
          },
        ],
        scores: { p1: 20, p2: 0 },
        highlights: null,
      },
      ctx,
    );

    expect(store.drawingHistory).toHaveLength(2);
    expect(store.drawingHistory.map((d) => d.round)).toEqual([1, 1]);
    expect(store.totalGuessesMade).toBe(2);

    // The next round nulls player.drawing — the captured history must persist.
    handleGameFlowEvent(
      {
        type: "start_round",
        round: 2,
        cards: { p1: { category: "X", items: ["a"] } },
      },
      ctx,
    );
    expect(store.drawingHistory).toHaveLength(2);
  });

  it("records a received reaction and ignores unknown reaction keys", () => {
    const reactions = useReactions();
    reactions.clear();

    handleResultsEvent(
      {
        type: "reaction_received",
        drawingId: "p2",
        reactionKey: "laugh",
        senderId: "p1",
      },
      ctx,
    );
    handleResultsEvent(
      {
        type: "reaction_received",
        drawingId: "p2",
        reactionKey: "bogus",
        senderId: "p1",
      } as never,
      ctx,
    );

    expect(reactions.countsFor("p2").laugh).toBe(1);
  });
});
