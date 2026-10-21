import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { useAnnouncer } from "@/composables/useAnnouncer";
import type { GamePhase } from "@/shared/types";

import { useGameStore } from "@/stores/game";
import RoomView from "@/views/RoomView.vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { roomCode: "ROOM1" } }),
}));

const connectMock = vi.fn();
vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    connect: connectMock,
    connectionStatus: ref("disconnected"),
  }),
}));

vi.mock("@/views/RoomAccessView.vue", () => ({
  default: { template: "<div>guest</div>" },
}));
vi.mock("@/views/SpectatorRoomView.vue", () => ({
  default: { template: "<main><h1>spectator</h1></main>" },
}));
vi.mock("@/views/LobbyView.vue", () => ({
  default: { template: "<main><h1>waiting</h1></main>" },
}));
vi.mock("@/views/GameView.vue", () => ({
  default: { template: "<main><h1>game</h1></main>" },
}));
vi.mock("@/views/RoundResultsView.vue", () => ({
  default: { template: "<div>round-results</div>" },
}));
vi.mock("@/views/ResultsView.vue", () => ({
  default: { template: "<div>final-results</div>" },
}));

describe("RoomView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useAnnouncer().message.value = "";
  });

  function joinRoom(phase: GamePhase) {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.roomCode = "ROOM1";
    store.hydrated = true;
    store.gamePhase = phase;
    store.currentRound = 2;
    return store;
  }

  it("falls back to the guest flow when the saved room code does not match the URL", () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.roomCode = "OLDROOM";
    store.gamePhase = "lobby";

    const wrapper = mount(RoomView);

    expect(wrapper.text()).toContain("guest");
  });

  it("drops spectator mode once the room returns to the lobby", () => {
    const store = useGameStore();
    store.isSpectatorMode = true;
    store.gamePhase = "lobby";
    store.roomCode = "ROOM1";

    const wrapper = mount(RoomView);

    expect(wrapper.text()).toContain("guest");
    expect(wrapper.text()).not.toContain("spectator");
  });

  it("moves focus to the new phase's heading, announces it and retitles the page", async () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.roomCode = "ROOM1";
    store.hydrated = true;
    store.gamePhase = "lobby";
    store.currentRound = 1;
    const { message } = useAnnouncer();

    const wrapper = mount(RoomView, { attachTo: document.body });
    expect(document.title).toBe("Lobby · Six Second Scribbles");

    store.gamePhase = "drawing";
    await nextTick();
    await nextTick();

    const heading = wrapper.get("h1").element;
    expect(document.activeElement).toBe(heading);
    expect(heading.getAttribute("tabindex")).toBe("-1");
    expect(message.value).toBe("Round 1: drawing");
    expect(document.title).toBe("Round 1: drawing · Six Second Scribbles");
    wrapper.unmount();
  });

  it.each<[GamePhase, string]>([
    ["guessing", "Round 2: guessing"],
    ["round_results", "Round 2 Results"],
    ["final_results", "Game over"],
  ])("names the %s screen and round in the tab title", (phase, title) => {
    joinRoom(phase);

    const wrapper = mount(RoomView);

    expect(document.title).toBe(`${title} · Six Second Scribbles`);
    wrapper.unmount();
  });

  it("titles the page as connecting until the room snapshot arrives, and says nothing yet", async () => {
    const store = joinRoom("lobby");
    store.hydrated = false;

    const wrapper = mount(RoomView);
    expect(wrapper.get("h1").text()).toBe("Connecting…");
    expect(document.title).toBe("Connecting… · Six Second Scribbles");

    store.gamePhase = "drawing";
    await nextTick();
    await nextTick();

    expect(useAnnouncer().message.value).toBe("");
    wrapper.unmount();
  });

  it("tells a spectator the phase changed without moving their focus", async () => {
    const store = useGameStore();
    store.isSpectatorMode = true;
    store.roomCode = "ROOM1";
    store.hydrated = true;
    store.gamePhase = "drawing";

    const wrapper = mount(RoomView, { attachTo: document.body });
    expect(document.title).toBe("Watching room · Six Second Scribbles");

    store.gamePhase = "guessing";
    await nextTick();
    await nextTick();

    expect(useAnnouncer().message.value).toBe("Watching room");
    expect(document.activeElement).toBe(document.body);
    wrapper.unmount();
  });

  it("still announces the phase when the new screen has no heading to focus", async () => {
    const store = joinRoom("round_results");

    const wrapper = mount(RoomView, { attachTo: document.body });
    store.gamePhase = "final_results";
    await nextTick();
    await nextTick();

    expect(useAnnouncer().message.value).toBe("Game over");
    expect(document.activeElement).toBe(document.body);
    wrapper.unmount();
  });
});
