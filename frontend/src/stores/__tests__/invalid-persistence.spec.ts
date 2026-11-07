import { flushSync } from "svelte";
import { expect, it } from "vitest";
import { STORAGE_KEYS } from "@/config/gameConfig";

it("ignores malformed stored preferences", async () => {
  localStorage.setItem(
    STORAGE_KEYS.GAME_STATE,
    JSON.stringify({
      localPlayerId: 42,
      localPlayerName: {},
      localPlayerColor: "red",
      localPadVisible: "false",
    }),
  );
  const { useGameStore } = await import("@/stores/game.svelte");
  const store = useGameStore();
  expect(store.localPlayerId).toBe("");
  expect(store.localPlayerName).toBe("");
  expect(store.localPlayerColor).toBeNull();
  expect(store.localPadVisible).toBe(true);
  flushSync();
});
