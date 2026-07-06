import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomeCreateJoin from "@/components/home/HomeCreateJoin.vue";
import { i18n } from "@/i18n";
import { useGameStore } from "@/stores/game";

const apiRequestMock = vi.fn();
const connectMock = vi.fn();
const openForNameMock = vi.fn();
const pushMock = vi.fn();
const showNotificationMock = vi.fn();

vi.mock("@/lib/api", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}));

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({ connect: connectMock }),
}));

vi.mock("@/composables/useSettingsPanel", () => ({
  useSettingsPanel: () => ({ openForName: openForNameMock }),
}));

vi.mock("@/composables/notifications", () => ({
  showNotification: (...args: unknown[]) => showNotificationMock(...args),
}));

vi.mock("@/shared/nameGenerator", () => ({
  generateRandomName: () => "Sketchy Guest",
}));

vi.mock("@/shared/playerIdentity", () => ({
  getOrCreatePlayerId: () => "player-1",
}));

vi.mock("vue-router", () => ({
  useRouter: () => ({ push: pushMock }),
}));

function mountPanel() {
  return mount(HomeCreateJoin, {
    global: {
      plugins: [i18n],
    },
  });
}

describe("HomeCreateJoin", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    apiRequestMock.mockReset();
    connectMock.mockReset();
    openForNameMock.mockReset();
    pushMock.mockReset();
    showNotificationMock.mockReset();
  });

  it("opens the name prompt before creating a room without a player name", async () => {
    const wrapper = mountPanel();

    await wrapper.findAll("button")[0].trigger("click");

    expect(openForNameMock).toHaveBeenCalledWith(expect.any(Function));
    expect(apiRequestMock).not.toHaveBeenCalled();
  });

  it("creates a room and navigates when the player has a name", async () => {
    const store = useGameStore();
    store.localPlayerName = "Simon";
    apiRequestMock.mockResolvedValueOnce({ room_code: "ABC123" });

    const wrapper = mountPanel();
    await wrapper.findAll("button")[0].trigger("click");
    await flushPromises();

    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/rooms",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(store.localPlayerId).toBe("player-1");
    expect(store.roomCode).toBe("ABC123");
    expect(connectMock).toHaveBeenCalledWith("ABC123");
    expect(pushMock).toHaveBeenCalledWith({ name: "room", params: { roomCode: "ABC123" } });
  });

  it("quick play assigns a generated name before joining a room", async () => {
    apiRequestMock.mockResolvedValueOnce({ room_code: "FAST01" });
    const store = useGameStore();

    const wrapper = mountPanel();
    await wrapper.findAll("button").at(-1)?.trigger("click");
    await flushPromises();

    expect(store.localPlayerName).toBe("Sketchy Guest");
    expect(apiRequestMock).toHaveBeenCalledWith(
      "/api/rooms/quick-play",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(connectMock).toHaveBeenCalledWith("FAST01");
  });

  it("reports an invalid room code before checking the backend", async () => {
    const store = useGameStore();
    store.localPlayerName = "Simon";
    const wrapper = mountPanel();

    await wrapper.find("input").setValue("NOPE");
    await wrapper.findAll("button")[1].trigger("click");

    expect(showNotificationMock).toHaveBeenCalledWith(
      expect.stringContaining("Room code must be 6 characters"),
      "error",
    );
    expect(apiRequestMock).not.toHaveBeenCalled();
  });
});
