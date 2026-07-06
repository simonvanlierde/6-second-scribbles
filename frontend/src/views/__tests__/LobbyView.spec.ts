import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";
import LobbyView from "@/views/LobbyView.vue";

const sendMock = vi.fn();
const copyMock = vi.fn();
const showNotificationMock = vi.fn();
const leaveRoomMock = vi.fn();

vi.mock("@vueuse/core", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@vueuse/core")>();
  return {
    ...actual,
    useClipboard: () => ({ copy: copyMock }),
  };
});

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

vi.mock("@/composables/notifications", () => ({
  useNotifications: () => ({ showNotification: showNotificationMock }),
}));

vi.mock("@/composables/useLeaveRoom", () => ({
  useLeaveRoom: () => ({ leaveRoom: leaveRoomMock }),
}));

vi.mock("vue-router", () => ({
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
  return mount(LobbyView, {
    global: {
      plugins: [i18n],
      stubs: {
        GameSettingsPanel: { template: '<div data-testid="settings-panel" />' },
        PlayerListPanel: { template: '<div data-testid="player-list" />' },
        SharedDrawpad: { template: '<div data-testid="shared-drawpad" />' },
      },
    },
  });
}

describe("LobbyView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sendMock.mockReset();
    copyMock.mockReset();
    showNotificationMock.mockReset();
    leaveRoomMock.mockReset();
  });

  it("renders host controls and starts the game", async () => {
    seedLobby();
    const wrapper = mountLobby();

    expect(wrapper.text()).toContain("Players (2)");
    expect(wrapper.find('[data-testid="player-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="settings-panel"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="shared-drawpad"]').exists()).toBe(true);

    await wrapper.find(".lobby-main__start").trigger("click");

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

    await wrapper.find(".lobby-code").trigger("click");

    expect(copyMock).toHaveBeenCalledWith("ABC123");
    expect(showNotificationMock).toHaveBeenCalledWith("Copied!");
  });

  it("lets the host manage shared drawpad visibility and clearing", async () => {
    const store = seedLobby();
    store.applyPartialStroke("p2", { color: "#000", width: 2, points: [{ x: 1, y: 1 }] }, true);
    const wrapper = mountLobby();

    await wrapper.find('[aria-label="Clear for all"]').trigger("click");
    expect(store.currentStrokes).toHaveLength(0);
    expect(sendMock).toHaveBeenCalledWith({ type: "drawpad_clear" });

    await wrapper.find('[aria-label="Hide for all"]').trigger("click");
    expect(store.roomPadVisible).toBe(false);
    expect(sendMock).toHaveBeenCalledWith({ type: "pad_visibility", visible: false });
  });

  it("shows waiting copy for non-host players and toggles their local pad", async () => {
    const store = seedLobby({ host: false });
    const wrapper = mountLobby();

    expect(wrapper.text()).toContain("Waiting for host to start the game");
    expect(wrapper.find(".lobby-main__start").exists()).toBe(false);

    await wrapper.find('[aria-label="Hide my pad"]').trigger("click");

    expect(store.localPadVisible).toBe(false);
  });
});
