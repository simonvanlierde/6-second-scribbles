import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { cardDecks } from "@/shared/cardDecks";
import { useGameStore } from "@/stores/game";

// Mock useGameConnection so no WebSocket is opened
vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    send: vi.fn(),
    connect: vi.fn(),
    handleMessage: vi.fn(),
  }),
}));

// Import after mocking
const { useGameEngine } = await import("@/composables/useGameEngine");

beforeEach(() => {
  setActivePinia(createPinia());
});

// ---------------------------------------------------------------------------
// getRandomCard
// ---------------------------------------------------------------------------

describe("getRandomCard", () => {
  it("returns a card from the correct difficulty deck", () => {
    const { getRandomCard } = useGameEngine();
    const card = getRandomCard("easy");
    expect(cardDecks.easy).toContainEqual(card);
  });

  it("works for all difficulties", () => {
    const { getRandomCard } = useGameEngine();
    for (const diff of ["easy", "medium", "hard"] as const) {
      const card = getRandomCard(diff);
      expect(card).toHaveProperty("category");
      expect(card).toHaveProperty("items");
    }
  });

  it("throws for an invalid difficulty", () => {
    const { getRandomCard } = useGameEngine();
    // @ts-expect-error intentionally bad input
    expect(() => getRandomCard("extreme")).toThrow();
  });
});

// ---------------------------------------------------------------------------
// assignCards
// ---------------------------------------------------------------------------

describe("assignCards", () => {
  it("assigns a card to every player", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");

    const { assignCards } = useGameEngine();
    const cards = assignCards("medium");

    expect(Object.keys(cards)).toHaveLength(2);
    expect(cards.p1).toHaveProperty("category");
    expect(cards.p2).toHaveProperty("category");
  });

  it("all assigned cards come from the correct deck", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    store.addPlayer("p2", "Bob");
    store.addPlayer("p3", "Carol");

    const { assignCards } = useGameEngine();
    const cards = assignCards("hard");

    for (const card of Object.values(cards)) {
      expect(cardDecks.hard).toContainEqual(card);
    }
  });

  it("handles more players than cards via modulo cycling", () => {
    const store = useGameStore();
    // Add more players than there are cards in any single deck (stress test)
    const deckSize = cardDecks.easy.length;
    for (let i = 0; i < deckSize + 2; i++) {
      store.addPlayer(`p${i}`, `Player ${i}`);
    }

    const { assignCards } = useGameEngine();
    const cards = assignCards("easy");
    expect(Object.keys(cards)).toHaveLength(deckSize + 2);
  });

  it("returns an empty object when there are no players", () => {
    const { assignCards } = useGameEngine();
    const cards = assignCards("easy");
    expect(cards).toEqual({});
  });

  it("throws for an invalid difficulty", () => {
    const store = useGameStore();
    store.addPlayer("p1", "Alice");
    const { assignCards } = useGameEngine();
    // @ts-expect-error intentionally bad input
    expect(() => assignCards("extreme")).toThrow();
  });
});
