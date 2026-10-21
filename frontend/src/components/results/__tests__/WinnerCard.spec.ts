import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import WinnerCard from "@/components/results/WinnerCard.vue";

// Matches any emoji — structural UI must contain none (reactions are the only exception).
const EMOJI = /\p{Extended_Pictographic}/u;

const alice = { name: "Alice", color: "#ffb4a2" };
const bob = { name: "Bob", color: "#b5e6b5" };

describe("WinnerCard", () => {
  it("renders the winner name, score and avatar", () => {
    const wrapper = mount(WinnerCard, { props: { name: "Alice", winners: [alice], score: 42 } });

    expect(wrapper.text()).toContain("Alice");
    expect(wrapper.text()).toContain("42 pts");
    expect(wrapper.findAll(".hd-avatar--lg")).toHaveLength(1);
  });

  it("shows the singular champion ribbon for a sole winner", () => {
    const wrapper = mount(WinnerCard, { props: { name: "Alice", winners: [alice], score: 42 } });
    expect(wrapper.find(".winner-card__ribbon").text()).toBe("Champion");
  });

  it("shows the plural ribbon, all names and one avatar per player for a tie", () => {
    const wrapper = mount(WinnerCard, { props: { name: "Alice and Bob", winners: [alice, bob], score: 42 } });
    expect(wrapper.find(".winner-card__ribbon").text()).toBe("Champions");
    expect(wrapper.text()).toContain("Alice and Bob");
    expect(wrapper.findAll(".hd-avatar--lg").map((a) => a.text())).toEqual(["A", "B"]);
  });

  it("crowns nobody when nobody scored", () => {
    const wrapper = mount(WinnerCard, { props: { name: "Alice and Bob", winners: [alice, bob], score: 0 } });
    expect(wrapper.text()).toContain("No winner this time");
    expect(wrapper.text()).not.toContain("Alice");
    expect(wrapper.find(".winner-card__ribbon").exists()).toBe(false);
    expect(wrapper.find(".hd-avatar").exists()).toBe(false);
  });

  it("contains no emoji", () => {
    const wrapper = mount(WinnerCard, { props: { name: "Alice", winners: [alice], score: 42 } });
    expect(EMOJI.test(wrapper.text())).toBe(false);
  });
});
