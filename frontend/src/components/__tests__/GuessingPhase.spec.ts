import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import GuessingPhase from "@/components/GuessingPhase.vue";
import { useGameStore } from "@/stores/game";

const sendMock = vi.fn();
const playMock = vi.fn();
const leaveRoomMock = vi.fn();
const draftRestoreMock = vi.fn();
const draftClearMock = vi.fn();

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/useGameTimer", () => ({
  useGameTimer: () => ({ timeLeft: ref(30), isWarning: ref(false), stop: vi.fn() }),
}));

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

vi.mock("@/composables/useRoundDraft", () => ({
  useRoundDraft: () => ({ restore: draftRestoreMock, clear: draftClearMock }),
}));

vi.mock("@/composables/useSound", () => ({
  useSound: () => ({ play: playMock }),
}));

function seedGuessing() {
  const store = useGameStore();
  store.setPlayers([
    { id: "p1", name: "Alice" },
    { id: "p2", name: "Bob" },
  ]);
  store.localPlayerId = "p1";
  store.setPlayerDrawing("p2", "data:image/png;base64,BBBB");
  store.startGuessing(Date.now(), { p1: "p2" });
  return store;
}

describe("GuessingPhase", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
    sendMock.mockReset();
    playMock.mockReset();
    leaveRoomMock.mockReset();
    draftRestoreMock.mockReset();
    draftClearMock.mockReset();
    seedGuessing();
  });

  it("renders the assigned drawing and seeds an empty guess input", () => {
    const wrapper = mount(GuessingPhase);

    expect(wrapper.text()).toContain("Guess Bob's drawing");
    expect(wrapper.find("img.drawing-frame__img").attributes("src")).toBe("data:image/png;base64,BBBB");
    expect(wrapper.findAll("input.guess-input")).toHaveLength(1);
    expect(draftRestoreMock).toHaveBeenCalledTimes(1);
  });

  it("adds another input as guesses are typed and submits non-empty guesses", async () => {
    const wrapper = mount(GuessingPhase);

    await wrapper.find("input.guess-input").setValue("cat");

    expect(wrapper.findAll("input.guess-input")).toHaveLength(2);

    await wrapper.find(".guess-card__submit").trigger("click");

    expect(playMock).toHaveBeenCalledWith("click");
    expect(sendMock).toHaveBeenCalledWith({
      type: "submit_guess",
      playerId: "p1",
      targetPlayerId: "p2",
      guesses: ["cat"],
    });
    expect(sendMock).toHaveBeenCalledWith({ type: "player_ready", playerId: "p1" });
    expect(draftClearMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Guesses submitted");
  });

  it("confirms before submitting an empty guess list", async () => {
    const wrapper = mount(GuessingPhase);

    await wrapper.find(".guess-card__submit").trigger("click");

    expect(wrapper.text()).toContain("No guesses entered");
    expect(sendMock).not.toHaveBeenCalledWith(expect.objectContaining({ type: "submit_guess" }));

    await wrapper.findAll('[data-testid="hd-dialog-confirm"]').at(-1)?.trigger("click");

    expect(sendMock).toHaveBeenCalledWith({
      type: "submit_guess",
      playerId: "p1",
      targetPlayerId: "p2",
      guesses: [],
    });
  });

  it("shows a waiting state when no drawing is assigned", () => {
    const store = useGameStore();
    store.guessTargets = {};

    const wrapper = mount(GuessingPhase);

    expect(wrapper.text()).toContain("Waiting for your assigned drawing");
  });
});
