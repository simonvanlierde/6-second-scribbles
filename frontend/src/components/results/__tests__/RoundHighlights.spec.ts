import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import RoundHighlights from "@/components/results/RoundHighlights.vue";
import type { RoundHighlights as RoundHighlightsData } from "@/shared/types";
import { useGameStore } from "@/stores/game";

function seedPlayers() {
  const store = useGameStore();
  store.setPlayers([
    { id: "p1", name: "Alice" },
    { id: "p2", name: "Bob" },
    { id: "p3", name: "Carol" },
  ]);
}

beforeEach(() => {
  setActivePinia(createPinia());
  seedPlayers();
});

describe("RoundHighlights", () => {
  it("renders a card per present highlight with the winner's name and detail", () => {
    const highlights: RoundHighlightsData = {
      bestGuesser: { playerId: "p1", detail: "3/4" },
      speedDemon: { playerId: "p2", detail: "" },
      wildestMiss: { playerId: "p3", detail: "banana" },
    };

    const wrapper = mount(RoundHighlights, { props: { highlights } });

    const cards = wrapper.findAll(".highlight");
    expect(cards).toHaveLength(3);
    expect(wrapper.text()).toContain("Alice");
    expect(wrapper.text()).toContain("Got 3/4 right");
    expect(wrapper.text()).toContain("First to guess");
    expect(wrapper.text()).toContain("banana");
    // Middle card uses the post-it variant for rhythm.
    expect(cards[1]?.classes()).toContain("hd-card--postit");
  });

  it("skips highlights that are null", () => {
    const highlights: RoundHighlightsData = {
      bestGuesser: { playerId: "p1", detail: "2/2" },
      speedDemon: null,
      wildestMiss: null,
    };

    const wrapper = mount(RoundHighlights, { props: { highlights } });

    expect(wrapper.findAll(".highlight")).toHaveLength(1);
  });

  it("shows a fallback when there are no highlights", () => {
    const wrapper = mount(RoundHighlights, { props: { highlights: null } });

    expect(wrapper.findAll(".highlight")).toHaveLength(0);
    expect(wrapper.text()).toContain("No highlights this round");
  });
});
