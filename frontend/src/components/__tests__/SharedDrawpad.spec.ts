import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import SharedDrawpad from "@/components/SharedDrawpad.vue";
import { useGameStore } from "@/stores/game";

const canvasMocks = vi.hoisted(() => ({
  clear: vi.fn(),
  cleanup: vi.fn(),
  drawStroke: vi.fn(),
  initCanvas: vi.fn(),
  setColor: vi.fn(),
  setStrokeProgressCallback: vi.fn(),
  setWidth: vi.fn(),
}));

const sendMock = vi.hoisted(() => vi.fn());

vi.mock("@/composables/useDrawingCanvas", () => ({
  useDrawingCanvas: () => ({
    ...canvasMocks,
  }),
}));

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

const DrawingCanvasStageStub = defineComponent({
  name: "DrawingCanvasStage",
  setup(_, { slots }) {
    return () => h("div", { class: "stage-stub" }, slots.default?.());
  },
});

const DrawingToolbarStub = defineComponent({
  name: "DrawingToolbar",
  emits: ["clear", "select-color", "select-size"],
  setup(_, { emit }) {
    return () =>
      h("div", [
        h("button", { class: "clear", onClick: () => emit("clear") }, "clear"),
        h("button", { class: "color", onClick: () => emit("select-color", "#f00") }, "color"),
        h("button", { class: "size", onClick: () => emit("select-size", 9) }, "size"),
      ]);
  },
});

describe("SharedDrawpad", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sendMock.mockReset();
    for (const mock of Object.values(canvasMocks)) mock.mockReset();
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", vi.fn());
  });

  it("initializes the canvas and replays existing lobby strokes", () => {
    const store = useGameStore();
    store.currentStrokes = [{ color: "#000", width: 4, points: [{ x: 1, y: 2 }] }];

    mount(SharedDrawpad, {
      global: {
        stubs: {
          DrawingCanvasStage: DrawingCanvasStageStub,
          DrawingToolbar: DrawingToolbarStub,
        },
      },
    });

    expect(canvasMocks.initCanvas).toHaveBeenCalledWith(expect.any(HTMLCanvasElement));
    expect(canvasMocks.drawStroke).toHaveBeenCalledWith(store.currentStrokes[0]);
    expect(canvasMocks.setStrokeProgressCallback).toHaveBeenCalledWith(expect.any(Function));
  });

  it("flushes stroke progress as partial draw events", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";

    mount(SharedDrawpad, {
      global: {
        stubs: {
          DrawingCanvasStage: DrawingCanvasStageStub,
          DrawingToolbar: DrawingToolbarStub,
        },
      },
    });

    const callback = canvasMocks.setStrokeProgressCallback.mock.calls[0]?.[0];
    callback({
      color: "#123",
      width: 6,
      points: [
        { x: 1, y: 1 },
        { x: 2, y: 2 },
      ],
      first: true,
    });

    expect(sendMock).toHaveBeenCalledWith({
      type: "draw_stroke_partial",
      playerId: "p1",
      stroke: {
        color: "#123",
        width: 6,
        points: [
          { x: 1, y: 1 },
          { x: 2, y: 2 },
        ],
      },
      strokeStart: true,
    });
  });

  it("clears locally and forwards toolbar choices to the canvas", async () => {
    const wrapper = mount(SharedDrawpad, {
      global: {
        stubs: {
          DrawingCanvasStage: DrawingCanvasStageStub,
          DrawingToolbar: DrawingToolbarStub,
        },
      },
    });

    await wrapper.find(".clear").trigger("click");
    await wrapper.find(".color").trigger("click");
    await wrapper.find(".size").trigger("click");

    expect(canvasMocks.clear).toHaveBeenCalledTimes(1);
    expect(canvasMocks.setColor).toHaveBeenCalledWith("#f00");
    expect(canvasMocks.setWidth).toHaveBeenCalledWith(9);
  });
});
