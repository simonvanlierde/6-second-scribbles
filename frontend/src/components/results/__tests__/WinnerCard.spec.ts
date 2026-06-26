import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WinnerCard from "@/components/results/WinnerCard.vue";

// Matches any emoji — structural UI must contain none (reactions are the only exception).
const EMOJI = /\p{Extended_Pictographic}/u;

describe("WinnerCard", () => {
  it("renders the winner name, score and avatar", () => {
    const wrapper = mount(WinnerCard, {
      props: { name: "Alice", initial: "A", color: "#ffb4a2", score: 42, isTie: false },
    });

    expect(wrapper.text()).toContain("Alice");
    expect(wrapper.text()).toContain("42 pts");
    expect(wrapper.find(".hd-avatar--lg").exists()).toBe(true);
  });

  it("shows the singular champion ribbon for a sole winner", () => {
    const wrapper = mount(WinnerCard, {
      props: { name: "Alice", initial: "A", color: "#ffb4a2", score: 42, isTie: false },
    });
    expect(wrapper.find(".winner-card__ribbon").text()).toBe("Champion");
  });

  it("shows the plural champions ribbon and all names for a tie", () => {
    const wrapper = mount(WinnerCard, {
      props: { name: "Alice and Bob", initial: "A", color: "#ffb4a2", score: 42, isTie: true },
    });
    expect(wrapper.find(".winner-card__ribbon").text()).toBe("Champions");
    expect(wrapper.text()).toContain("Alice and Bob");
  });

  it("contains no emoji", () => {
    const wrapper = mount(WinnerCard, {
      props: { name: "Alice", initial: "A", color: "#ffb4a2", score: 42, isTie: false },
    });
    expect(EMOJI.test(wrapper.text())).toBe(false);
  });
});
