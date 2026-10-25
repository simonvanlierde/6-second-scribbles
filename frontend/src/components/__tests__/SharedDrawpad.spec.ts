import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, nextTick, ref } from "vue";

import SharedDrawpad from "@/components/SharedDrawpad.vue";
import { useGameStore } from "@/stores/game";

const canvasMocks = vi.hoisted(() => ({
  clear: vi.fn(),
  cleanup: vi.fn(),
  commitStroke: vi.fn(),
  initCanvas: vi.fn(),
  replaceStrokes: vi.fn(),
  setColor: vi.fn(),
  setLiveStroke: vi.fn(),
  setResizeHandler: vi.fn(),
  setStrokeProgressCallback: vi.fn(),
  setWidth: vi.fn(),
  size: vi.fn(),
}));

const sendMock = vi.hoisted(() => vi.fn());

// Not in canvasMocks, whose entries are all reset as mocks before each test.
const isDrawing = vi.hoisted(() => ({ value: false }));

vi.mock("@/composables/useDrawingCanvas", () => ({
  useDrawingCanvas: () => ({
    ...canvasMocks,
    isDrawing,
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
    expect(canvasMocks.replaceStrokes).toHaveBeenCalledWith([{ color: "#000", width: 4, points: [{ x: 100, y: 20 }] }]);
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
    canvasMocks.replaceStrokes.mockClear();

    canvasMocks.size.mockReturnValue({ width: 400, height: 300 });
    canvasMocks.setResizeHandler.mock.calls[0]?.[0]();

    expect(canvasMocks.replaceStrokes).toHaveBeenCalledWith([
      { color: "#000", width: 4, points: [{ x: 200, y: 150 }] },
    ]);
  });

  it("shows a remote stroke as live and commits it once fragments stop", async () => {
    const store = useGameStore();
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });

    store.applyPartialStroke("p2", { color: "#f00", width: 4, points: [0, 0] }, true);
    await nextTick();
    store.applyPartialStroke("p2", { color: "#f00", width: 4, points: [10000, 10000] }, false);
    await nextTick();

    const grown = {
      color: "#f00",
      width: 4,
      points: [
        { x: 0, y: 0 },
        { x: 200, y: 100 },
      ],
    };
    const stroke = store.currentStrokes[0];
    expect(canvasMocks.setLiveStroke).toHaveBeenLastCalledWith(stroke, grown);
    vi.advanceTimersByTime(299);
    expect(canvasMocks.commitStroke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(canvasMocks.commitStroke).toHaveBeenCalledWith(grown, stroke);
  });

  it("commits a remote stroke as soon as its player starts the next one", async () => {
    const store = useGameStore();
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });

    store.applyPartialStroke("p2", { color: "#f00", width: 4, points: [0, 0] }, true);
    store.applyPartialStroke("p3", { color: "#00f", width: 4, points: [0, 0] }, true);
    await nextTick();
    store.applyPartialStroke("p2", { color: "#f00", width: 4, points: [5000, 5000] }, true);
    await nextTick();

    expect(canvasMocks.commitStroke).toHaveBeenCalledTimes(1);
    expect(canvasMocks.commitStroke).toHaveBeenCalledWith(
      { color: "#f00", width: 4, points: [{ x: 0, y: 0 }] },
      store.currentStrokes[0],
    );
    expect(canvasMocks.setLiveStroke).toHaveBeenLastCalledWith(store.currentStrokes[2], {
      color: "#f00",
      width: 4,
      points: [{ x: 100, y: 50 }],
    });
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
    canvasMocks.replaceStrokes.mockClear();

    canvasMocks.setResizeHandler.mock.calls[0]?.[0]();
    store.applyPartialStroke("p2", { color: "#f00", width: 4, points: [1000, 1000] }, true);
    await wrapper.vm.$nextTick();

    // Only the stroke drawn after the clear comes back.
    expect(canvasMocks.replaceStrokes).toHaveBeenCalledWith([]);
    expect(canvasMocks.setLiveStroke).toHaveBeenCalledTimes(1);
    expect(canvasMocks.setLiveStroke).toHaveBeenCalledWith(
      store.currentStrokes[1],
      expect.objectContaining({ color: "#f00" }),
    );
  });

  it("fills strokes from a room_state snapshot once each, not as live strokes", async () => {
    const store = useGameStore();
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });

    // As a room_state snapshot hydrates the store: the strokes, then one version bump.
    store.currentStrokes = [1, 2, 3].map((n) => ({ color: "#000", width: 4, points: [n * 1000, n * 1000] }));
    store.strokesVersion++;
    await nextTick();

    expect(canvasMocks.setLiveStroke).not.toHaveBeenCalled();
    expect(canvasMocks.commitStroke).toHaveBeenCalledTimes(3);
  });

  it("leaves our own unfinished stroke out of a resize redraw, since it is still live", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    canvasMocks.setStrokeProgressCallback.mock.calls[0]?.[0]({
      color: "#123",
      width: 6,
      points: [{ x: 100, y: 50 }],
      first: true,
    });
    vi.advanceTimersByTime(50);
    const resize = canvasMocks.setResizeHandler.mock.calls[0]?.[0];

    isDrawing.value = true;
    resize();
    expect(canvasMocks.replaceStrokes).toHaveBeenLastCalledWith([]);

    isDrawing.value = false;
    resize();
    expect(canvasMocks.replaceStrokes).toHaveBeenLastCalledWith([expect.objectContaining({ color: "#123" })]);
  });

  it("forgets the oldest strokes past the server's cap and redraws the rest", async () => {
    const store = useGameStore();
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    // 25 players' worth of strokes, 1,000 points each: 25,000 points, 5,000 over the cap.
    for (let i = 0; i < 25; i++) {
      store.applyPartialStroke(`p${i}`, { color: "#000", width: 4, points: Array(2000).fill(i) }, true);
    }
    const pointsHeld = store.currentStrokes.reduce((sum, s) => sum + s.points.length / 2, 0);
    expect(pointsHeld).toBe(20_000);
    expect(store.currentStrokes[0]?.points[0]).toBe(5);
    await nextTick();

    canvasMocks.replaceStrokes.mockClear();
    canvasMocks.setResizeHandler.mock.calls[0]?.[0]();
    // Every stroke is still its player's latest, so all 20 are redrawn live.
    expect(canvasMocks.replaceStrokes).toHaveBeenCalledWith([]);
    expect(new Set(canvasMocks.setLiveStroke.mock.calls.slice(-20).map((call) => call[0])).size).toBe(20);
  });

  it("starts a new stroke when a trim dropped the player's stroke in progress", async () => {
    const store = useGameStore();
    mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    // p0's stroke is the oldest; five full-length strokes after it push the doodle past the cap.
    store.applyPartialStroke("p0", { color: "#000", width: 4, points: Array(4000).fill(0) }, true);
    for (let i = 1; i <= 5; i++) {
      store.applyPartialStroke(`p${i}`, { color: "#000", width: 4, points: Array(8000).fill(i) }, true);
    }
    expect(store.currentStrokes).toHaveLength(5);
    expect(store.currentStrokes.some((s) => s.points[0] === 0)).toBe(false);

    // Not a start fragment: the server also begins a new stroke, as it no longer holds p0's.
    store.applyPartialStroke("p0", { color: "#f00", width: 4, points: [7, 7] }, false);

    expect(store.currentStrokes).toHaveLength(5);
    expect(store.currentStrokes.at(-1)?.points).toEqual([7, 7]);
  });

  it("keeps strokes cleared locally after a trim off the pad", async () => {
    const store = useGameStore();
    const wrapper = mount(SharedDrawpad, {
      global: { stubs: { DrawingCanvasStage: DrawingCanvasStageStub, DrawingToolbar: DrawingToolbarStub } },
    });
    for (let i = 0; i < 6; i++) {
      store.applyPartialStroke(`p${i}`, { color: "#000", width: 4, points: Array(8000).fill(i) }, true);
    }
    expect(store.currentStrokes).toHaveLength(5);
    await nextTick();

    await wrapper.find(".clear").trigger("click");
    canvasMocks.replaceStrokes.mockClear();
    canvasMocks.setLiveStroke.mockClear();
    canvasMocks.setResizeHandler.mock.calls[0]?.[0]();

    expect(canvasMocks.replaceStrokes).toHaveBeenCalledWith([]);
    expect(canvasMocks.setLiveStroke).not.toHaveBeenCalled();
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
