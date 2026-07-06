import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DrawingRevealGrid from "@/components/results/DrawingRevealGrid.vue";
import { useReactions } from "@/composables/useReactions";
import { useGameStore } from "@/stores/game";

const sendMock = vi.fn();

vi.mock("@/composables/useGameConnection", () => ({
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
  setActivePinia(createPinia());
  sendMock.mockClear();
  useReactions().clear();
  seedDrawings();
});

describe("DrawingRevealGrid", () => {
  it("renders one cell per drawing", () => {
    const wrapper = mount(DrawingRevealGrid);
    expect(wrapper.findAll(".reveal__cell")).toHaveLength(2);
  });

  it("sends a reaction_send event when a reaction is tapped", async () => {
    const wrapper = mount(DrawingRevealGrid);

    // First reaction button of the first drawing's pad.
    await wrapper.find('[aria-label="React with laugh"]').trigger("click");

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

    const wrapper = mount(DrawingRevealGrid);
    await wrapper.vm.$nextTick();

    const badge = wrapper.find(".reveal__badge");
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toContain("2");
  });
});
