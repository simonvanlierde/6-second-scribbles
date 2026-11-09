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
import LobbyView from "@/views/LobbyView.svelte";

const sendMock = vi.fn();
const copyMock = vi.fn();
const showNotificationMock = vi.fn();
const leaveRoomMock = vi.fn();

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/notifications.svelte", () => ({
  useNotifications: () => ({ showNotification: showNotificationMock }),
}));

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

vi.mock("@/router", () => ({
  useRoute: () => ({ params: { roomCode: "ABC123" } }),
}));

function seedLobby({ host = true } = {}) {
  const store = useGameStore();
  store.setPlayers([
    { id: "p1", name: "Host" },
    { id: "p2", name: "Player" },
  ]);
  store.localPlayerId = host ? "p1" : "p2";
  store.setHost("p1");
  store.applySettingsUpdate({
    difficulty: "medium",
    rounds: 4,
    drawingTimeLimit: 60,
    guessingTimeLimit: 45,
  });
  return store;
}

function mountLobby() {
  return render(LobbyView);
}

describe("LobbyView", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().localPlayerId = "";
    sendMock.mockReset();
    copyMock.mockReset();
    Object.defineProperty(navigator, "clipboard", { value: { writeText: copyMock }, configurable: true });
    showNotificationMock.mockReset();
    leaveRoomMock.mockReset();
  });

  it("renders host controls and starts the game", async () => {
    seedLobby();
    const wrapper = mountLobby();

    expect(wrapper.container.textContent).toContain("Players (2)");
    expect(Boolean(wrapper.container.querySelector(".player-list"))).toBe(true);
    expect(Boolean(wrapper.container.querySelector(".settings-panel"))).toBe(true);
    expect(Boolean(wrapper.container.querySelector(".shared-drawpad"))).toBe(true);

    await fireEvent.click(wrapper.container.querySelector(".lobby-main__start")!);

    expect(sendMock).toHaveBeenCalledWith({
      type: "start_game",
      difficulty: "medium",
      rounds: 4,
      drawingTimeLimit: 60,
      guessingTimeLimit: 45,
    });
  });

  it("copies the room code and shows a notification", async () => {
    seedLobby();
    const wrapper = mountLobby();

    await fireEvent.click(wrapper.container.querySelector(".lobby-code")!);

    expect(copyMock).toHaveBeenCalledWith("ABC123");
    expect(showNotificationMock).toHaveBeenCalledWith("Copied!");
  });

  it("does not claim the code was copied when clipboard access is denied", async () => {
    seedLobby();
    copyMock.mockRejectedValueOnce(new DOMException("Write permission denied.", "NotAllowedError"));
    const wrapper = mountLobby();

    await fireEvent.click(wrapper.container.querySelector(".lobby-code")!);
    await flushPromises();

    expect(copyMock).toHaveBeenCalledWith("ABC123");
    expect(showNotificationMock).not.toHaveBeenCalled();
  });

  it("lets the host manage shared drawpad visibility and clearing", async () => {
    const store = seedLobby();
    store.applyPartialStroke("p2", { color: "#000", width: 2, points: [1, 1] }, true);
    const wrapper = mountLobby();

    await fireEvent.click(wrapper.container.querySelector('[aria-label="Clear for all"]')!);
    expect(store.currentStrokes).toHaveLength(0);
    expect(sendMock).toHaveBeenCalledWith({ type: "drawpad_clear" });

    await fireEvent.click(wrapper.container.querySelector('[aria-label="Hide for all"]')!);
    expect(store.roomPadVisible).toBe(false);
    expect(sendMock).toHaveBeenCalledWith({ type: "pad_visibility", visible: false });
  });

  it("shows waiting copy for non-host players and toggles their local pad", async () => {
    const store = seedLobby({ host: false });
    const wrapper = mountLobby();

    expect(wrapper.container.textContent).toContain("Waiting for host to start the game");
    expect(Boolean(wrapper.container.querySelector(".lobby-main__start"))).toBe(false);

    await fireEvent.click(wrapper.container.querySelector('[aria-label="Hide my pad"]')!);

    expect(store.localPadVisible).toBe(false);
  });
});

vi.mock("@/components/SharedDrawpad.svelte", async () => ({
  default: (await import("./fixtures/SharedDrawpad.svelte")).default,
}));
vi.mock("@/components/GameSettingsPanel.svelte", async () => ({
  default: (await import("./fixtures/GameSettingsPanel.svelte")).default,
}));
vi.mock("@/components/PlayerListPanel.svelte", async () => ({
  default: (await import("./fixtures/PlayerListPanel.svelte")).default,
}));
