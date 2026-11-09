import { fireEvent, render } from "@testing-library/svelte";
import { tick } from "svelte";

const flushPromises = async () => {
  await Promise.resolve();
  await tick();
  await Promise.resolve();
  await tick();
};

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useGameStore } from "@/stores/game.svelte";
import RoundResultsView from "@/views/RoundResultsView.svelte";

const leaveRoomMock = vi.fn();
const playMock = vi.fn();

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

vi.mock("@/composables/useSound.svelte", () => ({
  useSound: () => ({ play: playMock }),
}));

function seedRoundResults() {
  const store = useGameStore();
  store.setPlayers([
    { id: "p1", name: "Alice" },
    { id: "p2", name: "Bob" },
    { id: "p3", name: "Carol", connected: false },
  ]);
  store.localPlayerId = "p2";
  store.currentRound = 2;
  store.maxRounds = 3;
  store.setPlayerDrawing("p1", "data:image/png;base64,AAAA");
  store.onRoundComplete({
    results: [
      {
        playerId: "p2",
        targetPlayerId: "p1",
        correctGuesses: 3,
        totalItems: 5,
        pointsEarned: 6,
      },
    ],
    scores: { p1: 8, p2: 12, p3: 4 },
    highlights: {
      bestGuesser: { playerId: "p2", detail: "3/5" },
      speedDemon: null,
      wildestMiss: null,
    },
  });
  return store;
}

describe("RoundResultsView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useGameStore().reset();
    useGameStore().localPlayerId = "";
    leaveRoomMock.mockReset();
    playMock.mockReset();
    seedRoundResults();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders grouped round performance and score standings", () => {
    const wrapper = render(RoundResultsView);

    expect(playMock).toHaveBeenCalledWith("reveal");
    expect(wrapper.container.textContent).toContain("Round 2 Results");
    expect(wrapper.container.textContent).toContain("Alice's drawing");
    expect(wrapper.container.textContent).toContain("3/5");
    expect(wrapper.container.textContent).toContain("+6 pts");
    expect(wrapper.container.textContent).toContain("No guesses submitted");

    const standings = Array.from(wrapper.container.querySelectorAll(".standings__row")).map((row) => row.textContent);
    expect(standings[0]).toContain("Bob");
    expect(standings[0]).toContain("12 pts");
    expect(standings[0]).toContain("You");
    expect(standings[2]).toContain("Carol");
  });

  it("counts down once per second", async () => {
    const wrapper = render(RoundResultsView);

    expect(wrapper.container.querySelector(".game-header__timer")?.textContent).toContain("15");

    vi.advanceTimersByTime(2_000);
    await flushPromises();

    expect(wrapper.container.querySelector(".game-header__timer")?.textContent).toContain("13");
  });

  it("leaves immediately when no confirmation is required", async () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Solo" }]);
    store.localPlayerId = "p1";
    store.setHost("p1");

    const wrapper = render(RoundResultsView);
    await fireEvent.click(wrapper.container.querySelector('[aria-label="Leave"]')!);

    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });

  it("says the next round is coming, and after the last round that the final results are", () => {
    const store = useGameStore();
    expect(render(RoundResultsView).container.querySelector(".round-results__lead")?.textContent).toContain(
      "Next round",
    );

    store.currentRound = 3;
    expect(render(RoundResultsView).container.querySelector(".round-results__lead")?.textContent).toContain(
      "Final results",
    );
  });
});
