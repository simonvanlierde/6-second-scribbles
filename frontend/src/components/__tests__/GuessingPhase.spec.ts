import { fireEvent, render } from "@testing-library/svelte";
import { tick as nextTick } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import GuessingPhase from "@/components/GuessingPhase.svelte";
import { useGameStore } from "@/stores/game.svelte";

const sendMock = vi.fn();
const playMock = vi.fn();
const leaveRoomMock = vi.fn();
const draftRestoreMock = vi.fn();
const draftClearMock = vi.fn();

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/useGameTimer.svelte", () => ({
  useGameTimer: () => ({ timeLeft: 30, isWarning: false, stop: vi.fn() }),
}));

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

vi.mock("@/composables/useRoundDraft", () => ({
  useRoundDraft: () => ({ restore: draftRestoreMock, clear: draftClearMock }),
}));

vi.mock("@/composables/useSound.svelte", () => ({
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
  store.onStartGuessing({ guessingStartTime: Date.now(), guessTargets: { p1: "p2" } });
  return store;
}

describe("GuessingPhase", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
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
    const wrapper = render(GuessingPhase);

    expect(wrapper.container.textContent).toContain("Guess Bob's drawing");
    expect(wrapper.container.querySelector("img.drawing-frame__img")?.getAttribute("src")).toBe(
      "data:image/png;base64,BBBB",
    );
    expect(wrapper.container.querySelectorAll("input.guess-input")).toHaveLength(1);
    expect(draftRestoreMock).toHaveBeenCalledTimes(1);
  });

  it("adds another input as guesses are typed and submits non-empty guesses", async () => {
    const wrapper = render(GuessingPhase);

    await fireEvent.input(wrapper.container.querySelector("input.guess-input") as HTMLElement, {
      target: { value: "cat" },
    });

    expect(wrapper.container.querySelectorAll("input.guess-input")).toHaveLength(2);

    await fireEvent.click(wrapper.container.querySelector(".guess-card__submit") as HTMLElement);

    expect(playMock).toHaveBeenCalledWith("click");
    expect(sendMock).toHaveBeenCalledWith({
      type: "submit_guess",
      playerId: "p1",
      targetPlayerId: "p2",
      guesses: ["cat"],
    });
    expect(sendMock).toHaveBeenCalledWith({ type: "player_ready", playerId: "p1" });
    expect(draftClearMock).toHaveBeenCalledTimes(1);
    expect(wrapper.container.textContent).toContain("Guesses submitted");
  });

  it("keeps the scrolling guess panel reachable by keyboard once nothing in it can take focus", async () => {
    const wrapper = render(GuessingPhase);
    const panel = wrapper.container.querySelector(".guess-panel") as HTMLElement;
    expect(panel.getAttribute("aria-label")).toBe("Your guesses");

    await fireEvent.input(wrapper.container.querySelector("input.guess-input") as HTMLElement, {
      target: { value: "cat" },
    });
    await fireEvent.click(wrapper.container.querySelector(".guess-card__submit") as HTMLElement);

    expect(panel.getAttribute("tabindex")).toBe("0");
  });

  it("keeps keyboard focus on the guess panel when submitting removes the button", async () => {
    const wrapper = render(GuessingPhase);
    await fireEvent.input(wrapper.container.querySelector("input.guess-input") as HTMLElement, {
      target: { value: "cat" },
    });
    await fireEvent.click(wrapper.container.querySelector(".guess-card__submit") as HTMLElement);
    await nextTick();

    expect(document.activeElement).toBe(wrapper.container.querySelector(".guess-panel"));
    wrapper.unmount();
  });

  it("confirms before submitting an empty guess list", async () => {
    const wrapper = render(GuessingPhase);

    await fireEvent.click(wrapper.container.querySelector(".guess-card__submit") as HTMLElement);

    expect(wrapper.container.textContent).toContain("No guesses entered");
    expect(sendMock).not.toHaveBeenCalledWith(expect.objectContaining({ type: "submit_guess" }));

    await fireEvent.click(wrapper.getAllByTestId("hd-dialog-confirm")[1] as HTMLElement);

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

    const wrapper = render(GuessingPhase);

    expect(wrapper.container.textContent).toContain("Waiting for your assigned drawing");
  });

  it("asks before leaving mid-guessing from the header", async () => {
    const wrapper = render(GuessingPhase);

    await fireEvent.click(wrapper.getByRole("button", { name: "Leave", exact: true }));
    await nextTick();

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
    expect(leaveRoomMock).not.toHaveBeenCalled();
  });
});
