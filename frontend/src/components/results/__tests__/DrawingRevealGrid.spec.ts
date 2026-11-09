import { fireEvent, render } from "@testing-library/svelte";
import { tick } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DrawingRevealGrid from "@/components/results/DrawingRevealGrid.svelte";
import { useReactions } from "@/composables/useReactions.svelte";
import { useGameStore } from "@/stores/game.svelte";

const sendMock = vi.fn();

vi.mock("@/composables/useGameConnection.svelte", () => ({
  useGameConnection: () => ({ send: sendMock }),
}));

function seedDrawings() {
  const store = useGameStore();
  store.setPlayers([
    { id: "p1", name: "Alice" },
    { id: "p2", name: "Bob" },
  ]);
  store.setPlayerDrawing("p1", "data:image/png;base64,AAAA");
  store.setPlayerDrawing("p2", "data:image/png;base64,BBBB");
}

beforeEach(() => {
  useGameStore().reset();
  useGameStore().setLocalPlayer("", "");
  sendMock.mockClear();
  useReactions().clear();
  seedDrawings();
});

describe("DrawingRevealGrid", () => {
  it("renders one cell per drawing", () => {
    const wrapper = render(DrawingRevealGrid);
    expect(Array.from(wrapper.container.querySelectorAll(".reveal__cell"))).toHaveLength(2);
  });

  it("sends a reaction_send event when a reaction is tapped", async () => {
    const wrapper = render(DrawingRevealGrid);

    // First reaction button of the first drawing's pad.
    await fireEvent.click(wrapper.container.querySelector('[aria-label="Laugh for Alice\'s drawing"]')!);

    expect(sendMock).toHaveBeenCalledWith({
      type: "reaction_send",
      drawingId: "p1",
      reactionKey: "laugh",
    });
  });

  it("renders accumulated reaction badges from the reactions store", async () => {
    const reactions = useReactions();
    reactions.add("p1", "laugh");
    reactions.add("p1", "laugh");

    const wrapper = render(DrawingRevealGrid);
    await tick();

    const badge = wrapper.container.querySelector(".reveal__badge")!;
    expect(badge !== null).toBe(true);
    expect(badge.textContent!).toContain("2");
  });
});
