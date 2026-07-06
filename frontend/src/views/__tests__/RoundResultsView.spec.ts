import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useGameStore } from "@/stores/game";
import RoundResultsView from "@/views/RoundResultsView.vue";

const leaveRoomMock = vi.fn();
const playMock = vi.fn();

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

vi.mock("@/composables/useSound", () => ({
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
  store.updateScores({ p1: 8, p2: 12, p3: 4 });
  store.currentRound = 2;
  store.maxRounds = 3;
  store.setPlayerDrawing("p1", "data:image/png;base64,AAAA");
  store.setRoundResults([
    {
      playerId: "p2",
      targetPlayerId: "p1",
      correctGuesses: 3,
      totalItems: 5,
      pointsEarned: 6,
    },
  ]);
  store.setRoundHighlights({
    bestGuesser: { playerId: "p2", detail: "3/5" },
    speedDemon: null,
    wildestMiss: null,
  });
  return store;
}

describe("RoundResultsView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    leaveRoomMock.mockReset();
    playMock.mockReset();
    seedRoundResults();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders grouped round performance and score standings", () => {
    const wrapper = mount(RoundResultsView);

    expect(playMock).toHaveBeenCalledWith("reveal");
    expect(wrapper.text()).toContain("Round 2 Results");
    expect(wrapper.text()).toContain("Alice's drawing");
    expect(wrapper.text()).toContain("3/5");
    expect(wrapper.text()).toContain("+6 pts");
    expect(wrapper.text()).toContain("No guesses submitted");

    const standings = wrapper.findAll(".standings__row").map((row) => row.text());
    expect(standings[0]).toContain("Bob");
    expect(standings[0]).toContain("12 pts");
    expect(standings[0]).toContain("You");
    expect(standings[2]).toContain("Carol");
  });

  it("counts down once per second", async () => {
    const wrapper = mount(RoundResultsView);

    expect(wrapper.find(".game-header__timer").text()).toContain("15");

    vi.advanceTimersByTime(2_000);
    await flushPromises();

    expect(wrapper.find(".game-header__timer").text()).toContain("13");
  });

  it("leaves immediately when no confirmation is required", async () => {
    const store = useGameStore();
    store.setPlayers([{ id: "p1", name: "Solo" }]);
    store.localPlayerId = "p1";
    store.setHost("p1");

    const wrapper = mount(RoundResultsView);
    await wrapper.find('[aria-label="Leave"]').trigger("click");

    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });
});
