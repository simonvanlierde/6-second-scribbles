import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import SharedDrawpad from "@/components/SharedDrawpad.vue";
import { useGameStore } from "@/stores/game";

const canvasMocks = vi.hoisted(() => ({
  clear: vi.fn(),
  cleanup: vi.fn(),
  drawStroke: vi.fn(),
  initCanvas: vi.fn(),
  setColor: vi.fn(),
  setResizeHandler: vi.fn(),
  setStrokeProgressCallback: vi.fn(),
  setWidth: vi.fn(),
  size: vi.fn(),
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
    vi.useFakeTimers();
    canvasMocks.size.mockReturnValue({ width: 200, height: 100 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("initializes the canvas and replays existing lobby strokes", () => {
    const store = useGameStore();
    // Halfway across and a fifth down the 200 x 100 pad.
    store.currentStrokes = [{ color: "#000", width: 4, points: [5000, 2000] }];

    mount(SharedDrawpad, {
      global: {
        stubs: {
          DrawingCanvasStage: DrawingCanvasStageStub,
          DrawingToolbar: DrawingToolbarStub,
        },
      },
    });

    expect(canvasMocks.initCanvas).toHaveBeenCalledWith(expect.any(HTMLCanvasElement));
    expect(canvasMocks.drawStroke).toHaveBeenCalledWith({ color: "#000", width: 4, points: [{ x: 100, y: 20 }] });
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
        { x: 50, y: 25 },
        { x: 200, y: 100 },
      ],
      first: true,
    });
    expect(sendMock).not.toHaveBeenCalled();

    vi.advanceTimersByTime(50);
    expect(sendMock).toHaveBeenCalledWith({
      type: "draw_stroke_partial",
      playerId: "p1",
      stroke: {
        color: "#123",
        width: 6,
        points: [2500, 2500, 10000, 10000],
      },
      strokeStart: true,
    });
    // Our own stroke joins the room's doodle, so a resize can redraw it.
    expect(store.currentStrokes).toEqual([{ color: "#123", width: 6, points: [2500, 2500, 10000, 10000] }]);
  });

  it("redraws the whole doodle at the new size when the pad resizes", () => {
    const store = useGameStore();
    store.currentStrokes = [{ color: "#000", width: 4, points: [5000, 5000] }];
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    canvasMocks.drawStroke.mockClear();

    canvasMocks.size.mockReturnValue({ width: 400, height: 300 });
    canvasMocks.setResizeHandler.mock.calls[0]?.[0]();

    expect(canvasMocks.clear).toHaveBeenCalled();
    expect(canvasMocks.drawStroke).toHaveBeenCalledWith({ color: "#000", width: 4, points: [{ x: 200, y: 150 }] });
  });

  it("sends nothing for points buffered on a pad with no size", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    canvasMocks.size.mockReturnValue({ width: 0, height: 0 });

    canvasMocks.setStrokeProgressCallback.mock.calls[0]?.[0]({
      color: "#123",
      width: 6,
      points: [{ x: 5, y: 5 }],
      first: true,
    });
    vi.advanceTimersByTime(50);

    expect(sendMock).not.toHaveBeenCalled();
    expect(store.currentStrokes).toEqual([]);
  });

  it("sends buffered points before the pad leaves the page, while it still has a size", async () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    // Hidden the way the lobby hides it: a v-if in the parent.
    const shown = ref(true);
    const Parent = defineComponent({
      setup: () => () => (shown.value ? h(SharedDrawpad) : null),
    });
    mount(Parent, {
      attachTo: document.body,
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    // Like a real canvas: it has a size only while it is in the page.
    const el = canvasMocks.initCanvas.mock.calls[0]?.[0] as HTMLCanvasElement;
    canvasMocks.size.mockImplementation(() => (el.isConnected ? { width: 200, height: 100 } : { width: 0, height: 0 }));
    canvasMocks.setStrokeProgressCallback.mock.calls[0]?.[0]({
      color: "#123",
      width: 6,
      points: [{ x: 100, y: 50 }],
      first: true,
    });

    shown.value = false;
    await nextTick();

    expect(sendMock).toHaveBeenCalledWith(
      expect.objectContaining({ stroke: expect.objectContaining({ points: [5000, 5000] }) }),
    );
  });

  it("keeps a locally cleared pad clear when it resizes", async () => {
    const store = useGameStore();
    store.currentStrokes = [{ color: "#000", width: 4, points: [5000, 5000] }];
    const wrapper = mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    await wrapper.find(".clear").trigger("click");
    canvasMocks.drawStroke.mockClear();

    canvasMocks.setResizeHandler.mock.calls[0]?.[0]();
    store.applyPartialStroke("p2", { color: "#f00", width: 4, points: [1000, 1000] }, true);
    await wrapper.vm.$nextTick();

    // Only the stroke drawn after the clear comes back.
    expect(canvasMocks.drawStroke).toHaveBeenCalledTimes(1);
    expect(canvasMocks.drawStroke).toHaveBeenCalledWith(expect.objectContaining({ color: "#f00" }));
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
    canvasMocks.clear.mockClear(); // the first draw clears once

    await wrapper.find(".clear").trigger("click");
    await wrapper.find(".color").trigger("click");
    await wrapper.find(".size").trigger("click");

    expect(canvasMocks.clear).toHaveBeenCalledTimes(1);
    expect(canvasMocks.setColor).toHaveBeenCalledWith("#f00");
    expect(canvasMocks.setWidth).toHaveBeenCalledWith(9);
  });
});
