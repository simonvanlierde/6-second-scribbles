import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SpectatorRoomView from "@/views/SpectatorRoomView.vue";

const leaveRoomMock = vi.fn();

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({
    leaveRoom: leaveRoomMock,
  }),
}));

vi.mock("@/stores/game", () => ({
  useGameStore: () => ({
    roomCode: "ROOM1",
    gamePhase: "drawing",
    playersList: [
      { id: "p1", name: "Alice", score: 12, drawing: "data:image/png;base64,abc" },
      { id: "p2", name: "Bob", score: 9 },
    ],
  }),
}));

beforeEach(() => {
  leaveRoomMock.mockClear();
});

describe("SpectatorRoomView", () => {
  it("leaves immediately without a confirmation dialog", async () => {
    const wrapper = mount(SpectatorRoomView);

    expect(wrapper.find("dialog").exists()).toBe(false);

    await wrapper.get("button.leave-btn").trigger("click");

    expect(leaveRoomMock).toHaveBeenCalledTimes(1);
  });
});
