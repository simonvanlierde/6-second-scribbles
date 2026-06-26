import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useRoomLeave } from "@/composables/useRoomLeave";
import { useGameStore } from "@/stores/game";

describe("useRoomLeave", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("returns translated drawing-phase confirmation copy", () => {
    const store = useGameStore();
    store.gamePhase = "drawing";

    const { shouldConfirm, dialog } = useRoomLeave();

    expect(shouldConfirm.value).toBe(true);
    expect(dialog.value).toMatchObject({
      title: "Leave Game?",
      message: "Your drawing progress will be lost and the round will continue without you.",
      confirmLabel: "Leave",
      cancelLabel: "Stay",
    });
  });

  it("returns translated guessing-phase confirmation copy", () => {
    const store = useGameStore();
    store.gamePhase = "guessing";

    const { dialog } = useRoomLeave();

    expect(dialog.value).toMatchObject({
      title: "Leave Round?",
      message: "Your guesses will be lost and the round will continue without you.",
      confirmLabel: "Leave",
      cancelLabel: "Stay",
    });
  });

  it("returns translated host lobby confirmation copy", () => {
    const store = useGameStore();
    store.gamePhase = "lobby";
    store.localPlayerId = "p1";
    store.setPlayers([
      { id: "p1", name: "Host" },
      { id: "p2", name: "Guest" },
    ]);
    store.setHost("p1");

    const { shouldConfirm, dialog } = useRoomLeave();

    expect(shouldConfirm.value).toBe(true);
    expect(dialog.value).toMatchObject({
      title: "Leave Room?",
      message: "Host will pass to another player when you leave.",
      confirmLabel: "Leave room",
      cancelLabel: "Stay",
    });
  });

  it("falls back to translated default leave labels", () => {
    const store = useGameStore();
    store.gamePhase = "lobby";

    const { shouldConfirm, dialog } = useRoomLeave();

    expect(shouldConfirm.value).toBe(false);
    expect(dialog.value).toMatchObject({
      title: "Leave Room?",
      message: "",
      confirmLabel: "Leave",
      cancelLabel: "Cancel",
    });
  });
});
