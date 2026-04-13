import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGameStore } from "@/stores/game";
import RoomView from "@/views/RoomView.vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { roomCode: "ROOM1" } }),
}));

vi.mock("@/views/RoomEntryView.vue", () => ({ default: { template: "<div>guest</div>" } }));
vi.mock("@/views/SpectatorRoomView.vue", () => ({ default: { template: "<div>spectator</div>" } }));
vi.mock("@/views/LobbyView.vue", () => ({ default: { template: "<div>waiting</div>" } }));
vi.mock("@/views/GameView.vue", () => ({ default: { template: "<div>game</div>" } }));
vi.mock("@/views/RoundResultsView.vue", () => ({ default: { template: "<div>round-results</div>" } }));
vi.mock("@/views/ResultsView.vue", () => ({ default: { template: "<div>final-results</div>" } }));

describe("RoomView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("falls back to the guest flow when the saved room code does not match the URL", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.roomCode = "OLDROOM";
    store.gamePhase = "lobby";

    const wrapper = mount(RoomView);

    expect(wrapper.text()).toContain("guest");
  });
});
