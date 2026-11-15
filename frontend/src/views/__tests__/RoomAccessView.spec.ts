import { fireEvent, render } from "@testing-library/svelte";
import { tick } from "svelte";

const flushPromises = async () => {
  await Promise.resolve();
  await tick();
  await Promise.resolve();
  await tick();
};

import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGameStore } from "@/stores/game.svelte";
import RoomAccessView from "@/views/RoomAccessView.svelte";

const connectMock = vi.fn();
const fetchMock = vi.fn();
const routeState = { roomCode: "ROOM01" };

vi.mock("@/router", () => ({
  useRoute: () => ({
    params: routeState,
  }),
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({
    connect: connectMock,
  }),
}));

beforeEach(() => {
  useGameStore().reset();
  useGameStore().localPlayerId = "";
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

    const wrapper = render(RoomAccessView);

    await flushPromises();
    await tick();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(wrapper.container.textContent).toContain("Enter your name");
    expect(wrapper.container.textContent).toContain("Join room");
    expect(wrapper.container.textContent).toContain("2 players in room");
    expect(Boolean(wrapper.container.querySelector("dialog"))).toBe(false);
    expect(Boolean(wrapper.container.querySelector("input.name-input"))).toBe(true);
  });

  it("says why Join is disabled until a name is entered", async () => {
    useGameStore().localPlayerName = "";
    const wrapper = render(RoomAccessView);
    await flushPromises();
    await tick();

    const join = Array.from(wrapper.container.querySelectorAll("button")).find((button) =>
      button.textContent?.match(/join room/i),
    )!;
    const hint = wrapper.container.querySelector("#join-hint")!;
    expect(join.disabled).toBe(true);
    expect(hint.textContent).toContain("Enter your name to join");
    expect(join.getAttribute("aria-describedby")).toBe("join-hint");

    await fireEvent.input(wrapper.container.querySelector("input.name-input")!, { target: { value: "Ann" } });
    await tick();

    expect(join.disabled).toBe(false);
    expect(wrapper.container.querySelector("#join-hint")).toBeNull();
    expect(join.hasAttribute("aria-describedby")).toBe(false);
  });

  it("stops phones from autocorrecting the player name", async () => {
    const wrapper = render(RoomAccessView);
    await flushPromises();
    await tick();

    const name = wrapper.container.querySelector("input.name-input")!;
    expect(name.getAttribute("autocorrect")).toBe("off");
    expect(name.getAttribute("spellcheck")).toBe("false");
  });

  it("prefills the saved name but waits for an explicit join action", async () => {
    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = render(RoomAccessView);

    await flushPromises();
    await tick();

    expect((wrapper.container.querySelector("input.name-input")! as HTMLInputElement).value).toBe("Alice");
    expect(connectMock).not.toHaveBeenCalled();
  });

  it("joins the room only when the user clicks the join button", async () => {
    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = render(RoomAccessView);

    await flushPromises();
    await tick();

    const joinButton = Array.from(wrapper.container.querySelectorAll("button")).find((button) =>
      button.textContent?.match(/join room/i),
    );
    await fireEvent.click(joinButton!);

    expect(connectMock).toHaveBeenCalledWith("ROOM01");
    expect(store.roomCode).toBe("ROOM01");
  });

  it("switches to watch mode for an in-progress room", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: true, players: 2, game_phase: "drawing" }),
    } as Response);

    const store = useGameStore();
    store.localPlayerName = "Alice";

    const wrapper = render(RoomAccessView);

    await flushPromises();
    await tick();

    expect(wrapper.container.textContent).toContain("Game in progress");
    expect(wrapper.container.textContent).toContain("Watch room");

    const watchButton = Array.from(wrapper.container.querySelectorAll("button")).find((button) =>
      button.textContent?.match(/watch room/i),
    );
    await fireEvent.click(watchButton!);

    expect(connectMock).toHaveBeenCalledWith("ROOM01", { observeOnly: true });
    expect(store.localPlayerId).toBe("");
  });

  it("shows a friendly message for missing rooms", async () => {
    fetchMock.mockResolvedValueOnce({
      json: async () => ({ exists: false }),
    } as Response);

    const wrapper = render(RoomAccessView);

    await flushPromises();
    await tick();

    expect(wrapper.container.textContent).toContain("Room not found");
    expect(wrapper.container.textContent).toContain("This room does not exist.");
    expect(
      Array.from(wrapper.container.querySelectorAll("button")).some((button) =>
        button.textContent?.match(/back to home/i),
      ),
    ).toBe(true);
  });

  it("rejects invalid room codes before hitting the network", async () => {
    routeState.roomCode = "BAD!!";

    const wrapper = render(RoomAccessView);

    await flushPromises();
    await tick();

    expect(fetchMock).not.toHaveBeenCalled();
    expect(wrapper.container.textContent).toContain("Invalid room code");
    expect(wrapper.container.textContent).toContain("Room codes are 6 characters");
  });
});
