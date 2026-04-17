import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, reactive } from "vue";

import { useGameStore } from "@/stores/game";
import RoomAccessView from "@/views/RoomAccessView.vue";

const connectMock = vi.fn();
const fetchMock = vi.fn();
const routeState = reactive({ roomCode: "ROOM01" });

vi.mock("vue-router", () => ({
  useRoute: () => ({
    params: routeState,
  }),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    connect: connectMock,
  }),
}));

beforeEach(() => {
  setActivePinia(createPinia());
  routeState.roomCode = "ROOM01";
  connectMock.mockClear();
  fetchMock.mockReset();
  vi.stubGlobal(
    "fetch",
    fetchMock.mockResolvedValue({
      json: async () => ({ exists: true, players: 2, game_phase: "lobby" }),
    } as Response),
  );
});

describe("RoomAccessView", () => {
  it("renders the join form for an existing lobby room", async () => {
    const store = useGameStore();
    store.localPlayerName = "";

    const wrapper = mount(RoomAccessView);

    await flushPromises();
    await nextTick();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Enter your name");
    expect(wrapper.text()).toContain("Join room");
    expect(wrapper.text()).toContain("2 players in room");
    expect(wrapper.find("dialog").exists()).toBe(false);
    expect(wrapper.find("input.name-input").exists()).toBe(true);
  });

  it("prefills the saved name but waits for an explicit join action", async () => {
    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = mount(RoomAccessView);

    await flushPromises();
    await nextTick();

    expect((wrapper.get("input.name-input").element as HTMLInputElement).value).toBe("Alice");
    expect(connectMock).not.toHaveBeenCalled();
  });

  it("joins the room only when the user clicks the join button", async () => {
    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = mount(RoomAccessView);

    await flushPromises();
    await nextTick();

    const joinButton = wrapper.findAll("button").find((button) => button.text().match(/join room/i));
    await joinButton?.trigger("click");

    expect(connectMock).toHaveBeenCalledWith("ROOM01");
    expect(store.roomCode).toBe("ROOM01");
  });

  it("switches to watch mode for an in-progress room", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "drawing" }),
    } as Response);

    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = mount(RoomAccessView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Game in progress");
    expect(wrapper.text()).toContain("Watch room");

    const watchButton = wrapper.findAll("button").find((button) => button.text().match(/watch room/i));
    await watchButton?.trigger("click");

    expect(connectMock).toHaveBeenCalledWith("ROOM01", { observeOnly: true });
    expect(store.localPlayerId).toBe("");
  });

  it("shows a friendly message for missing rooms", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: false }),
    } as Response);

    const wrapper = mount(RoomAccessView);

    await flushPromises();
    await nextTick();

    expect(wrapper.text()).toContain("Room not found");
    expect(wrapper.text()).toContain("This room does not exist.");
    expect(wrapper.findAll("button").some((button) => button.text().match(/back to lobby/i))).toBe(true);
  });

  it("rejects invalid room codes before hitting the network", async () => {
    routeState.roomCode = "BAD!!";

    const wrapper = mount(RoomAccessView);

    await flushPromises();
    await nextTick();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Invalid room code");
    expect(wrapper.text()).toContain("Room codes are 6 characters");
  });
});
