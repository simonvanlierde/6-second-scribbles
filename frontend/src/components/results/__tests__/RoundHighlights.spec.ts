import { render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it } from "vitest";

import RoundHighlights from "@/components/results/RoundHighlights.svelte";
import type { RoundHighlights as RoundHighlightsData } from "@/shared/types";
import { useGameStore } from "@/stores/game.svelte";

function seedPlayers() {
  const store = useGameStore();
  store.setPlayers([
    { id: "p1", name: "Alice" },
    { id: "p2", name: "Bob" },
    { id: "p3", name: "Carol" },
  ]);
}

beforeEach(() => {
  useGameStore().reset();
  useGameStore().setLocalPlayer("", "");
  seedPlayers();
});

describe("RoundHighlights", () => {
  it("renders a card per present highlight with the winner's name and detail", () => {
    const highlights: RoundHighlightsData = {
      bestGuesser: { playerId: "p1", detail: "3/4" },
      speedDemon: { playerId: "p2", detail: "" },
      wildestMiss: { playerId: "p3", detail: "banana" },
    };

    const wrapper = render(RoundHighlights, { props: { highlights } });

    const cards = Array.from(wrapper.container.querySelectorAll(".highlight"));
    expect(cards).toHaveLength(3);
    expect(wrapper.container.textContent!).toContain("Alice");
    expect(wrapper.container.textContent!).toContain("Got 3/4 right");
    expect(wrapper.container.textContent!).toContain("First to guess");
    expect(wrapper.container.textContent!).toContain("banana");
    // Middle card uses the post-it variant for rhythm.
    expect(cards[1]?.classList).toContain("hd-card--postit");
  });

  it("skips highlights that are null", () => {
    const highlights: RoundHighlightsData = {
      bestGuesser: { playerId: "p1", detail: "2/2" },
      speedDemon: null,
      wildestMiss: null,
    };

    const wrapper = render(RoundHighlights, { props: { highlights } });

    expect(Array.from(wrapper.container.querySelectorAll(".highlight"))).toHaveLength(1);
  });

  it("shows a fallback when there are no highlights", () => {
    const wrapper = render(RoundHighlights, { props: { highlights: null } });

    expect(Array.from(wrapper.container.querySelectorAll(".highlight"))).toHaveLength(0);
    expect(wrapper.container.textContent!).toContain("No highlights this round");
  });
});
