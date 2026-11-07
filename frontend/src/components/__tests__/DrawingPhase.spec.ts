import { fireEvent, render } from "@testing-library/svelte";
import { tick as nextTick } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DrawingPhase from "@/components/DrawingPhase.svelte";
import { DRAWING_PAPER } from "@/config/drawing";
import { useGameStore } from "@/stores/game.svelte";
import GameView from "@/views/GameView.svelte";

const canvasMocks = vi.hoisted(() => ({
  canvasRef: { toDataURL: () => "data:image/png;base64,DRAWING" },
  cleanup: vi.fn(),
  clear: vi.fn(),
  currentColor: "#111",
  currentWidth: 4,
  initCanvas: vi.fn(),
  replaceStrokes: vi.fn(),
  setColor: vi.fn(),
  setWidth: vi.fn(),
  strokes: [],
  undo: vi.fn(),
}));

const sendMock = vi.hoisted(() => vi.fn());
const playMock = vi.hoisted(() => vi.fn());
const draftRestoreMock = vi.hoisted(() => vi.fn());
const draftClearMock = vi.hoisted(() => vi.fn());
const leaveRoomMock = vi.hoisted(() => vi.fn());

vi.mock("@/composables/useDrawingCanvas.svelte", () => ({
  useDrawingCanvas: () => canvasMocks,
}));

const encodeDrawingMock = vi.hoisted(() => vi.fn(() => "data:image/webp;base64,DRAWING"));

vi.mock("@/lib/drawingImage", () => ({
  encodeDrawing: encodeDrawingMock,
}));

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/useGameTimer.svelte", () => ({
  useGameTimer: () => ({ timeLeft: 45, isWarning: false, stop: vi.fn() }),
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

function seedDrawing() {
  const store = useGameStore();
  store.setPlayers([{ id: "p1", name: "Alice" }]);
  store.localPlayerId = "p1";
  store.onStartRound({
    round: 1,
    cards: {
      p1: {
        category: "Animals",
        items: ["cat", "dog"],
      },
    },
  });
  return store;
}

function mountPhase() {
  return render(DrawingPhase);
}

describe("DrawingPhase", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
    for (const mock of Object.values(canvasMocks)) {
      if (typeof mock === "function") mock.mockReset();
    }
    sendMock.mockReset();
    playMock.mockReset();
    draftRestoreMock.mockReset();
    draftClearMock.mockReset();
    leaveRoomMock.mockReset();
    seedDrawing();
  });

  it("initializes the canvas and renders the assigned card", () => {
    const wrapper = mountPhase();

    expect(playMock).toHaveBeenCalledWith("roundStart");
    expect(canvasMocks.initCanvas).toHaveBeenCalledWith(expect.any(HTMLCanvasElement));
    expect(draftRestoreMock).toHaveBeenCalledTimes(1);
    expect(wrapper.container.textContent).toContain("Animals");
    expect(wrapper.container.textContent).toContain("cat");
  });

  it("toggles checklist items", async () => {
    const wrapper = mountPhase();
    const firstItem = wrapper.container.querySelector(".category-card__item") as HTMLElement;

    expect(firstItem.getAttribute("aria-pressed")).toBe("false");

    await fireEvent.click(firstItem);

    expect((wrapper.container.querySelector(".category-card__item") as HTMLElement).getAttribute("aria-pressed")).toBe(
      "true",
    );
  });

  it("submits the canvas drawing and ready status once", async () => {
    const store = useGameStore();
    const wrapper = mountPhase();

    await fireEvent.click(wrapper.container.querySelector(".drawing-phase__finish-desktop") as HTMLElement);
    await fireEvent.click(wrapper.container.querySelector(".drawing-phase__finish-desktop") as HTMLElement);

    expect(playMock).toHaveBeenCalledWith("click");
    expect(sendMock).toHaveBeenCalledWith({
      type: "draw_stroke",
      playerId: "p1",
      drawing: "data:image/webp;base64,DRAWING",
    });
    expect(encodeDrawingMock).toHaveBeenCalledWith(canvasMocks.canvasRef, expect.any(String));
    expect(sendMock).toHaveBeenCalledWith({ type: "player_ready", playerId: "p1" });
    expect(sendMock.mock.calls.filter(([event]) => event.type === "player_ready")).toHaveLength(1);
    expect(store.players.get("p1")?.drawing).toBe("data:image/webp;base64,DRAWING");
    expect(draftClearMock).toHaveBeenCalledTimes(1);
  });

  it("encodes the drawing over the fixed paper colour, whatever the theme", async () => {
    const wrapper = mountPhase();
    await fireEvent.click(wrapper.container.querySelector(".drawing-phase__finish-desktop") as HTMLElement);

    expect(encodeDrawingMock).toHaveBeenCalledWith(canvasMocks.canvasRef, DRAWING_PAPER);
  });

  it("still marks the player ready when the canvas is gone", async () => {
    const original = canvasMocks.canvasRef;
    canvasMocks.canvasRef = null as unknown as typeof original;
    try {
      const wrapper = mountPhase();
      await fireEvent.click(wrapper.container.querySelector(".drawing-phase__finish-desktop") as HTMLElement);

      expect(sendMock).not.toHaveBeenCalledWith(expect.objectContaining({ type: "draw_stroke" }));
      expect(sendMock).toHaveBeenCalledWith({ type: "player_ready", playerId: "p1" });
    } finally {
      canvasMocks.canvasRef = original;
    }
  });

  it("forwards toolbar actions to the drawing canvas", async () => {
    const wrapper = mountPhase();

    await fireEvent.click(wrapper.getByRole("button", { name: "Red", exact: true }));
    await fireEvent.click(wrapper.getByRole("button", { name: "Large brush", exact: true }));
    await fireEvent.click(wrapper.getByRole("button", { name: "Undo", exact: true }));
    await fireEvent.click(wrapper.getByRole("button", { name: "Clear", exact: true }));

    expect(canvasMocks.setColor).toHaveBeenCalledWith("#ff4d4d");
    expect(canvasMocks.setWidth).toHaveBeenCalledWith(10);
    expect(canvasMocks.undo).toHaveBeenCalledTimes(1);
    expect(canvasMocks.clear).toHaveBeenCalledTimes(1);
  });

  it("asks before leaving mid-drawing from the header", async () => {
    HTMLDialogElement.prototype.showModal = vi.fn(); // jsdom has no modal dialogs
    HTMLDialogElement.prototype.close = vi.fn();
    const wrapper = mountPhase();

    await fireEvent.click(wrapper.getByRole("button", { name: "Leave", exact: true }));
    await nextTick();

    expect(HTMLDialogElement.prototype.showModal).toHaveBeenCalled();
    expect(leaveRoomMock).not.toHaveBeenCalled();
  });
  it("submits the unfinished drawing when the server advances to guessing", async () => {
    const store = useGameStore();
    const wrapper = render(GameView);
    await nextTick();
    expect(canvasMocks.initCanvas).toHaveBeenCalledTimes(1);
    store.onStartGuessing({ guessingStartTime: Date.now(), guessTargets: {} });
    await nextTick();
    expect(store.gamePhase).toBe("guessing");
    expect(wrapper.container.querySelector(".guessing-phase")).not.toBeNull();
    expect(canvasMocks.cleanup).toHaveBeenCalledTimes(1);
    expect(encodeDrawingMock).toHaveBeenCalled();
    expect(sendMock).toHaveBeenCalledWith({
      type: "draw_stroke",
      playerId: "p1",
      drawing: "data:image/webp;base64,DRAWING",
    });
    expect(sendMock).toHaveBeenCalledWith({ type: "player_ready", playerId: "p1" });
  });
});
