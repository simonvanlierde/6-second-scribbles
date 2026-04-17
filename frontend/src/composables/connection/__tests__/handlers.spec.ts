import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import {
  type HandlerContext,
  handleConnectionEvent,
  handleGameFlowEvent,
  handleKickEvent,
} from "@/composables/connection/handlers";
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
});
