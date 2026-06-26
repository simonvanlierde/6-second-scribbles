import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import GameHeader from "@/components/game/GameHeader.vue";
import { useGameStore } from "@/stores/game";

describe("GameHeader", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders the timer value and round progress", () => {
    const store = useGameStore();
    store.currentRound = 2;
    store.maxRounds = 5;

    const wrapper = mount(GameHeader, { props: { timeLeft: 42 } });

    expect(wrapper.text()).toContain("42");
    expect(wrapper.text()).toContain("2");
  });

  it("emits leave when the leave button is clicked", async () => {
    const wrapper = mount(GameHeader, { props: { timeLeft: 30 } });

    await wrapper.get('button[aria-label="Leave"]').trigger("click");

    expect(wrapper.emitted("leave")).toHaveLength(1);
  });
});
