import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlayerListPanel from "@/components/PlayerListPanel.svelte";
import { useGameStore } from "@/stores/game.svelte";

const sendMock = vi.fn();

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({
    send: sendMock,
  }),
}));

describe("PlayerListPanel", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
    sendMock.mockClear();
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
  });

  function seedPlayers() {
    const store = useGameStore();
    store.setPlayers([
      { id: "p1", name: "Host" },
      { id: "p2", name: "Player Two" },
      { id: "p3", name: "Player Three" },
    ]);
    store.setHost("p1");
    return store;
  }

  function rowFor(wrapper: ReturnType<typeof render>, playerName: string) {
    const row = Array.from(wrapper.container.querySelectorAll("li")).find((item) =>
      item.textContent?.includes(playerName),
    );
    if (!row) throw new Error(`Missing row for ${playerName}`);
    return row;
  }

  it("shows Kick for the host on non-host rows", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p1";

    const wrapper = render(PlayerListPanel);

    expect(wrapper.container.textContent!).toContain("Kick");
    expect(wrapper.container.textContent!).not.toContain("Vote kick");
  });

  it("shows Vote kick for non-host players in public rooms only", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p2";
    store.setPrivacy(false);

    const wrapper = render(PlayerListPanel);
    const voteButtons = Array.from(wrapper.container.querySelectorAll("button")).filter(
      (button) => button.textContent?.trim() === "Vote kick",
    );
    const hostRow = Array.from(wrapper.container.querySelectorAll("li")).find((row) =>
      row.textContent?.includes("Host"),
    );

    expect(voteButtons).toHaveLength(1);
    expect(hostRow?.textContent).not.toContain("Vote kick");
  });

  it("hides Vote kick for non-host players in private rooms", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p2";
    store.setPrivacy(true);

    const wrapper = render(PlayerListPanel);

    expect(wrapper.container.textContent!).not.toContain("Vote kick");
  });

  it("uses different confirmation copy for host kick and vote-kick", async () => {
    const hostStore = seedPlayers();
    hostStore.localPlayerId = "p1";

    const hostWrapper = render(PlayerListPanel);
    await fireEvent.click(
      Array.from(hostWrapper.container.querySelectorAll("button")).find(
        (button) => button.textContent?.trim() === "Kick player",
      )!,
    );
    expect(hostWrapper.container.textContent!).toContain("Kick player?");

    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
    const playerStore = seedPlayers();
    playerStore.localPlayerId = "p2";
    playerStore.setPrivacy(false);

    const playerWrapper = render(PlayerListPanel);
    await fireEvent.click(
      Array.from(playerWrapper.container.querySelectorAll("button")).find(
        (button) => button.textContent?.trim() === "Vote kick",
      )!,
    );
    expect(playerWrapper.container.textContent!).toContain("Start vote-kick?");
  });

  it("casts a vote when a kick vote is already active", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p2";
    store.startKickVote("p3", {
      currentVotes: 1,
      requiredVotes: 2,
      expiresAt: Date.now() + 30_000,
    });

    const wrapper = render(PlayerListPanel);
    await fireEvent.click(
      Array.from(rowFor(wrapper, "Player Three").querySelectorAll("button")).find(
        (button) => button.textContent?.trim() === "Vote kick",
      )!,
    );

    expect(wrapper.container.textContent?.replace(/\s+/g, " ")).toContain("Vote: 1/2");
    expect(sendMock).toHaveBeenCalledWith({
      type: "cast_kick_vote",
      targetPlayerId: "p3",
    });
  });

  it("confirms a host kick by initiating a kick request", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p1";

    const wrapper = render(PlayerListPanel);
    await fireEvent.click(
      Array.from(rowFor(wrapper, "Player Two").querySelectorAll("button")).find(
        (button) => button.textContent?.trim() === "Kick player",
      )!,
    );
    await fireEvent.click(wrapper.container.querySelector('[data-testid="hd-dialog-confirm"]')!);

    expect(sendMock).toHaveBeenCalledWith({
      type: "initiate_kick",
      targetPlayerId: "p2",
    });
  });
});
