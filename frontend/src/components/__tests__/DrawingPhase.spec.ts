import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import DrawingPhase from "@/components/DrawingPhase.vue";
import { useGameStore } from "@/stores/game";

const canvasMocks = vi.hoisted(() => ({
  canvasRef: { value: { toDataURL: () => "data:image/png;base64,DRAWING" } },
  cleanup: vi.fn(),
  clear: vi.fn(),
  currentColor: { value: "#111" },
  currentWidth: { value: 4 },
  initCanvas: vi.fn(),
  replaceStrokes: vi.fn(),
  setColor: vi.fn(),
  setWidth: vi.fn(),
  strokes: { value: [] },
  undo: vi.fn(),
}));

const sendMock = vi.hoisted(() => vi.fn());
const playMock = vi.hoisted(() => vi.fn());
const draftRestoreMock = vi.hoisted(() => vi.fn());
const draftClearMock = vi.hoisted(() => vi.fn());

vi.mock("@/composables/useDrawingCanvas", () => ({
  useDrawingCanvas: () => canvasMocks,
}));

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/useGameTimer", () => ({
  useGameTimer: () => ({ timeLeft: ref(45), isWarning: ref(false), stop: vi.fn() }),
}));

vi.mock("@/composables/useRoundDraft", () => ({
  useRoundDraft: () => ({ restore: draftRestoreMock, clear: draftClearMock }),
}));

vi.mock("@/composables/useSound", () => ({
  useSound: () => ({ play: playMock }),
}));

const DrawingCanvasStageStub = defineComponent({
  name: "DrawingCanvasStage",
  setup(_, { slots }) {
    return () => h("div", { class: "stage-stub" }, slots.default?.());
  },
});

const DrawingToolbarStub = defineComponent({
  name: "DrawingToolbar",
  emits: ["clear", "select-color", "select-size", "undo"],
  setup(_, { emit }) {
    return () =>
      h("div", [
        h("button", { class: "color", onClick: () => emit("select-color", "#f00") }, "color"),
        h("button", { class: "size", onClick: () => emit("select-size", 8) }, "size"),
        h("button", { class: "undo", onClick: () => emit("undo") }, "undo"),
        h("button", { class: "clear", onClick: () => emit("clear") }, "clear"),
      ]);
  },
});

function seedDrawing() {
  const store = useGameStore();
  store.setPlayers([{ id: "p1", name: "Alice" }]);
  store.localPlayerId = "p1";
  store.startRound(1, {
    p1: {
      category: "Animals",
      items: ["cat", "dog"],
    },
  });
  return store;
}

function mountPhase() {
  return mount(DrawingPhase, {
    global: {
      stubs: {
        DrawingCanvasStage: DrawingCanvasStageStub,
        DrawingToolbar: DrawingToolbarStub,
      },
    },
  });
}

describe("DrawingPhase", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    for (const mock of Object.values(canvasMocks)) {
      if (typeof mock === "function") mock.mockReset();
    }
    sendMock.mockReset();
    playMock.mockReset();
    draftRestoreMock.mockReset();
    draftClearMock.mockReset();
    seedDrawing();
  });

  it("initializes the canvas and renders the assigned card", () => {
    const wrapper = mountPhase();

    expect(playMock).toHaveBeenCalledWith("roundStart");
    expect(canvasMocks.initCanvas).toHaveBeenCalledWith(expect.any(HTMLCanvasElement));
    expect(draftRestoreMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Animals");
    expect(wrapper.text()).toContain("cat");
  });

  it("toggles checklist items", async () => {
    const wrapper = mountPhase();
    const firstItem = wrapper.find(".category-card__item");

    expect(firstItem.attributes("aria-pressed")).toBe("false");

    await firstItem.trigger("click");

    expect(wrapper.find(".category-card__item").attributes("aria-pressed")).toBe("true");
  });

  it("submits the canvas drawing and ready status once", async () => {
    const store = useGameStore();
    const wrapper = mountPhase();

    await wrapper.find(".drawing-phase__finish-desktop").trigger("click");
    await wrapper.find(".drawing-phase__finish-desktop").trigger("click");

    expect(playMock).toHaveBeenCalledWith("click");
    expect(sendMock).toHaveBeenCalledWith({
      type: "draw_stroke",
      playerId: "p1",
      drawing: "data:image/png;base64,DRAWING",
    });
    expect(sendMock).toHaveBeenCalledWith({ type: "player_ready", playerId: "p1" });
    expect(sendMock.mock.calls.filter(([event]) => event.type === "player_ready")).toHaveLength(1);
    expect(store.players.get("p1")?.drawing).toBe("data:image/png;base64,DRAWING");
    expect(draftClearMock).toHaveBeenCalledTimes(1);
  });

  it("forwards toolbar actions to the drawing canvas", async () => {
    const wrapper = mountPhase();

    await wrapper.find(".color").trigger("click");
    await wrapper.find(".size").trigger("click");
    await wrapper.find(".undo").trigger("click");
    await wrapper.find(".clear").trigger("click");

    expect(canvasMocks.setColor).toHaveBeenCalledWith("#f00");
    expect(canvasMocks.setWidth).toHaveBeenCalledWith(8);
    expect(canvasMocks.undo).toHaveBeenCalledTimes(1);
    expect(canvasMocks.clear).toHaveBeenCalledTimes(1);
  });
});
