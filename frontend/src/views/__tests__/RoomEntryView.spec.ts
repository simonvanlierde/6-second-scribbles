import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useGameStore } from "@/stores/game";
import RoomEntryView from "@/views/RoomEntryView.vue";

const connectMock = vi.fn();
const leaveRoomMock = vi.fn();
const fetchMock = vi.fn();
let routeRoomCode = "ROOM01";

vi.mock("vue-router", () => ({
  useRoute: () => ({
    params: { roomCode: routeRoomCode },
  }),
}));

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    connect: connectMock,
  }),
}));
vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({
    leaveRoom: leaveRoomMock,
  }),
}));
vi.mock("@/views/SpectatorRoomView.vue", () => ({
  default: { template: "<div>Watching live updates</div>" },
}));
vi.mock("@/views/RoundResultsView.vue", () => ({
  default: { template: "<div>Round results preview</div>" },
}));
vi.mock("@/views/LobbyView.vue", () => ({
  default: { template: "<div>Waiting room preview</div>" },
}));
vi.mock("@/views/ResultsView.vue", () => ({
  default: { template: "<div>Final results preview</div>" },
}));

beforeEach(() => {
  setActivePinia(createPinia());
  routeRoomCode = "ROOM01";
  connectMock.mockClear();
  leaveRoomMock.mockClear();
  fetchMock.mockReset();
  vi.stubGlobal(
    "fetch",
    fetchMock.mockResolvedValue({
      json: async () => ({ exists: true, players: 2, game_phase: "lobby" }),
    } as Response),
  );
});

describe("RoomEntryView", () => {
  it("renders an inline name form instead of a dialog when no name is saved", async () => {
    const store = useGameStore();
    store.localPlayerName = "";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Enter your name");
    expect(wrapper.find("dialog").exists()).toBe(false);
    expect(wrapper.find("input.name-input").exists()).toBe(true);
    expect(wrapper.text()).toContain("Waiting room preview");
  });

  it("prefills the inline name field from saved state and joins the room", async () => {
    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect((wrapper.get("input.name-input").element as HTMLInputElement).value).toBe("Alice");

    await wrapper.get("button").trigger("click");
    const joinButton = wrapper.findAll("button").find((button) => button.text().match(/join room/i));
    await joinButton?.trigger("click");

    expect(connectMock).toHaveBeenCalledWith("ROOM01");
    expect(store.roomCode).toBe("ROOM01");
  });

  it("watches a room in progress instead of joining as a player", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "drawing" }),
    } as Response);

    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Watch room");
    expect(wrapper.find(".preview-room").exists()).toBe(true);

    const watchButton = wrapper.findAll("button").find((button) => button.text().match(/watch room/i));
    await watchButton?.trigger("click");

    expect(connectMock).toHaveBeenLastCalledWith("ROOM01", { observeOnly: true });
    expect(store.localPlayerId).toBe("");
  });

  it("shows round results behind the inline card during round results", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "round_results" }),
    } as Response);

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Round results preview");
    expect(wrapper.text()).toContain("Enter your name");
  });

  it("shows final results behind the inline card during final results", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "final_results" }),
    } as Response);

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Final results preview");
    expect(wrapper.text()).toContain("Enter your name");
  });

  it("shows a missing-room message and returns home after a timeout", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: false }),
    } as Response);

    vi.useFakeTimers();
    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Room not found");
    expect(wrapper.text()).toContain("bringing you back to the lobby");

    await vi.advanceTimersByTimeAsync(5000);
    expect(leaveRoomMock).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });

  it("auto-returns to lobby after an invalid room code", async () => {
    routeRoomCode = "BAD!!";

    vi.useFakeTimers();
    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Invalid room code");

    await vi.advanceTimersByTimeAsync(5000);
    expect(leaveRoomMock).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });
});
