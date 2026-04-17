import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SpectatorRoomView from "@/views/SpectatorRoomView.vue";

const disconnectMock = vi.fn();
const resetMock = vi.fn();
const routerPushMock = vi.fn();

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    disconnect: disconnectMock,
  }),
}));

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: routerPushMock }),
}));

vi.mock("@/stores/game", () => ({
  useGameStore: () => ({
    roomCode: "ROOM1",
    gamePhase: "drawing",
    playersList: [
      { id: "p1", name: "Alice", score: 12, drawing: "data:image/png;base64,abc" },
      { id: "p2", name: "Bob", score: 9 },
    ],
    reset: resetMock,
  }),
}));

beforeEach(() => {
  disconnectMock.mockClear();
  resetMock.mockClear();
  routerPushMock.mockClear();
});

describe("SpectatorRoomView", () => {
  it("leaves immediately without a confirmation dialog", async () => {
    const wrapper = mount(SpectatorRoomView);

    expect(wrapper.find("dialog").exists()).toBe(false);

    await wrapper.get("button.leave-btn").trigger("click");

    expect(disconnectMock).toHaveBeenCalledTimes(1);
    expect(resetMock).toHaveBeenCalledTimes(1);
    expect(routerPushMock).toHaveBeenCalledWith({ name: "home" });
  });
});
