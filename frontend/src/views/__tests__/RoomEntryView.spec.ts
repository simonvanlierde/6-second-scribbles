import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useGameStore } from "@/stores/game";
import RoomEntryView from "@/views/RoomEntryView.vue";

const connectMock = vi.fn();
const pushMock = vi.fn();
const fetchMock = vi.fn();
const leaveRoomMock = vi.fn();
let routeRoomCode = "ROOM01";

vi.mock("vue-router", () => ({
  useRoute: () => ({
    params: { roomCode: routeRoomCode },
  }),
  useRouter: () => ({
    push: pushMock,
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
  pushMock.mockClear();
  leaveRoomMock.mockClear();
  fetchMock.mockReset();
  vi.stubGlobal(
    "fetch",
    fetchMock.mockResolvedValue({
      json: async () => ({ exists: true, players: 2, game_phase: "lobby" }),
    } as Response),
  );

  HTMLDialogElement.prototype.close = vi.fn();
  HTMLDialogElement.prototype.showModal = vi.fn();
});

describe("RoomEntryView", () => {
  it("prompts for a name when none is saved", async () => {
    const store = useGameStore();
    store.localPlayerName = "";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Enter your name");
    expect(wrapper.text()).toContain("Waiting room preview");
    expect(wrapper.find(".guest-card").exists()).toBe(false);

    await wrapper.get("input.name-input").setValue("Guest Player");
    await wrapper.get("form.name-form").trigger("submit.prevent");

    expect(store.localPlayerName).toBe("Guest Player");
    expect(connectMock).toHaveBeenCalledWith("ROOM01");
  });

  it("joins an existing room when a name is already saved", async () => {
    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Join room");
    expect(wrapper.text()).toContain("Waiting room preview");

    await wrapper.get("form.name-form").trigger("submit.prevent");
    await flushPromises();

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

    await wrapper.get("form.name-form").trigger("submit.prevent");
    await flushPromises();

    expect(connectMock).toHaveBeenCalledWith("ROOM01", { observeOnly: true });
    expect(store.localPlayerId).toBe("");
  });

  it("shows round results behind the name modal during round results", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "round_results" }),
    } as Response);

    const store = useGameStore();
    store.localPlayerName = "";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Round results preview");
    expect(wrapper.text()).toContain("Enter your name");
  });

  it("shows final results behind the name modal during final results", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "final_results" }),
    } as Response);

    const store = useGameStore();
    store.localPlayerName = "";

    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Final results preview");
    expect(wrapper.text()).toContain("Enter your name");
  });

  it("shows a create action when the room does not exist", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: false }),
    } as Response);

    const store = useGameStore();
    store.localPlayerName = "Alice";

    vi.useFakeTimers();
    const wrapper = mount(RoomEntryView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Room not found");
    expect(wrapper.text()).toContain("This room does not exist, bringing you back to the lobby...");
    expect(wrapper.findAll("dialog")).toHaveLength(1);

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
