import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GameHeader from "@/components/game/GameHeader.svelte";
import { useGameStore } from "@/stores/game.svelte";

describe("GameHeader", () => {
  beforeEach(() => {
    useGameStore().reset();
    useGameStore().setLocalPlayer("", "");
  });

  it("renders the timer value and round progress", () => {
    const store = useGameStore();
    store.currentRound = 2;
    store.maxRounds = 5;

    const wrapper = render(GameHeader, { props: { timeLeft: 42 } });

    expect(wrapper.container.textContent!).toContain("42");
    expect(wrapper.container.textContent!).toContain("2");
  });

  it("emits leave when the leave button is clicked", async () => {
    const onleave = vi.fn();
    const wrapper = render(GameHeader, { props: { timeLeft: 30, onleave } });

    await fireEvent.click(wrapper.container.querySelector('button[aria-label="Leave"]')!);

    expect(onleave).toHaveBeenCalledTimes(1);
  });
});
