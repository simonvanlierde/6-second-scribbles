import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PlayerListPanel from "@/components/PlayerListPanel.vue";
import { useGameStore } from "@/stores/game";

const sendMock = vi.fn();

vi.mock("@/composables/useGameConnection", () => ({
  useGameConnection: () => ({
    send: sendMock,
  }),
}));

describe("PlayerListPanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
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

  it("shows Kick for the host on non-host rows", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p1";

    const wrapper = mount(PlayerListPanel);

    expect(wrapper.text()).toContain("Kick");
    expect(wrapper.text()).not.toContain("Vote kick");
  });

  it("shows Vote kick for non-host players in public rooms only", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p2";
    store.setPrivacy(false);

    const wrapper = mount(PlayerListPanel);
    const voteButtons = wrapper.findAll("button").filter((button) => button.text() === "Vote kick");
    const hostRow = wrapper.findAll("li").find((row) => row.text().includes("Host"));

    expect(voteButtons).toHaveLength(1);
    expect(hostRow?.text()).not.toContain("Vote kick");
  });

  it("hides Vote kick for non-host players in private rooms", async () => {
    const store = seedPlayers();
    store.localPlayerId = "p2";
    store.setPrivacy(true);

    const wrapper = mount(PlayerListPanel);

    expect(wrapper.text()).not.toContain("Vote kick");
  });

  it("uses different confirmation copy for host kick and vote-kick", async () => {
    const hostStore = seedPlayers();
    hostStore.localPlayerId = "p1";

    const hostWrapper = mount(PlayerListPanel);
    await hostWrapper
      .findAll("button")
      .find((button) => button.text() === "Kick")
      ?.trigger("click");
    expect(hostWrapper.text()).toContain("Kick player?");

    setActivePinia(createPinia());
    const playerStore = seedPlayers();
    playerStore.localPlayerId = "p2";
    playerStore.setPrivacy(false);

    const playerWrapper = mount(PlayerListPanel);
    await playerWrapper
      .findAll("button")
      .find((button) => button.text() === "Vote kick")
      ?.trigger("click");
    expect(playerWrapper.text()).toContain("Start vote-kick?");
  });
});
