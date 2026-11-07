import { render } from "@testing-library/svelte";
import { tick } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAnnouncer } from "@/composables/useAnnouncer.svelte";
import type { GamePhase } from "@/shared/types";

import { useGameStore } from "@/stores/game.svelte";
import RoomView from "@/views/RoomView.svelte";

vi.mock("@/router", () => ({
  useRoute: () => ({ params: { roomCode: "ROOM1" } }),
}));

const connectMock = vi.fn();
vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({
    connect: connectMock,
    connectionStatus: "disconnected",
  }),
}));

vi.mock("@/views/RoomAccessView.svelte", async () => ({
  default: (await import("./fixtures/RoomAccessView.svelte")).default,
}));
vi.mock("@/views/SpectatorRoomView.svelte", async () => ({
  default: (await import("./fixtures/SpectatorRoomView.svelte")).default,
}));
vi.mock("@/views/LobbyView.svelte", async () => ({
  default: (await import("./fixtures/LobbyView.svelte")).default,
}));
vi.mock("@/views/GameView.svelte", async () => ({
  default: (await import("./fixtures/GameView.svelte")).default,
}));
vi.mock("@/views/RoundResultsView.svelte", async () => ({
  default: (await import("./fixtures/RoundResultsView.svelte")).default,
}));
vi.mock("@/views/ResultsView.svelte", async () => ({
  default: (await import("./fixtures/ResultsView.svelte")).default,
}));

describe("RoomView", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().localPlayerId = "";
    useAnnouncer().message = "";
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

    const wrapper = render(RoomView);

    expect(wrapper.container.textContent).toContain("guest");
  });

  it("drops spectator mode once the room returns to the lobby", () => {
    const store = useGameStore();
    store.isSpectatorMode = true;
    store.gamePhase = "lobby";
    store.roomCode = "ROOM1";

    const wrapper = render(RoomView);

    expect(wrapper.container.textContent).toContain("guest");
    expect(wrapper.container.textContent).not.toContain("spectator");
  });

  it("moves focus to the new phase's heading, announces it and retitles the page", async () => {
    const store = useGameStore();
    store.localPlayerId = "p1";
    store.roomCode = "ROOM1";
    store.hydrated = true;
    store.gamePhase = "lobby";
    store.currentRound = 1;
    const announcer = useAnnouncer();

    const wrapper = render(RoomView);
    expect(document.title).toBe("Lobby · Six Second Scribbles");

    store.gamePhase = "drawing";
    await tick();
    await tick();

    const heading = wrapper.container.querySelector("h1")!;
    expect(document.activeElement).toBe(heading);
    expect(heading.getAttribute("tabindex")).toBe("-1");
    expect(announcer.message).toBe("Round 1: drawing");
    expect(document.title).toBe("Round 1: drawing · Six Second Scribbles");
    wrapper.unmount();
  });

  it.each<[GamePhase, string]>([
    ["guessing", "Round 2: guessing"],
    ["round_results", "Round 2 Results"],
    ["final_results", "Game over"],
  ])("names the %s screen and round in the tab title", (phase, title) => {
    joinRoom(phase);

    const wrapper = render(RoomView);

    expect(document.title).toBe(`${title} · Six Second Scribbles`);
    wrapper.unmount();
  });

  it("titles the page as connecting until the room snapshot arrives, and says nothing yet", async () => {
    const store = joinRoom("lobby");
    store.hydrated = false;

    const wrapper = render(RoomView);
    expect(wrapper.container.querySelector("h1")?.textContent).toBe("Connecting…");
    expect(document.title).toBe("Connecting… · Six Second Scribbles");

    store.gamePhase = "drawing";
    await tick();
    await tick();

    expect(useAnnouncer().message).toBe("");
    wrapper.unmount();
  });

  it("tells a spectator the phase changed without moving their focus", async () => {
    const store = useGameStore();
    store.isSpectatorMode = true;
    store.roomCode = "ROOM1";
    store.hydrated = true;
    store.gamePhase = "drawing";

    const wrapper = render(RoomView);
    expect(document.title).toBe("Watching room · Six Second Scribbles");

    store.gamePhase = "guessing";
    await tick();
    await tick();

    expect(useAnnouncer().message).toBe("Watching room");
    expect(document.activeElement).toBe(document.body);
    wrapper.unmount();
  });

  it("still announces the phase when the new screen has no heading to focus", async () => {
    const store = joinRoom("round_results");

    const wrapper = render(RoomView);
    store.gamePhase = "final_results";
    await tick();
    await tick();

    expect(useAnnouncer().message).toBe("Game over");
    expect(document.activeElement).toBe(document.body);
    wrapper.unmount();
  });
});
