import { render } from "@testing-library/svelte";
import { describe, expect, it } from "vitest";

import WinnerCard from "@/components/results/WinnerCard.svelte";

// Matches any emoji — structural UI must contain none (reactions are the only exception).
const EMOJI = /\p{Extended_Pictographic}/u;

const alice = { name: "Alice", color: "#ffb4a2" };
const bob = { name: "Bob", color: "#b5e6b5" };

describe("WinnerCard", () => {
  it("renders the winner name, score and avatar", () => {
    const wrapper = render(WinnerCard, { props: { name: "Alice", winners: [alice], score: 42 } });

    expect(wrapper.container.textContent!).toContain("Alice");
    expect(wrapper.container.textContent!).toContain("42 pts");
    expect(Array.from(wrapper.container.querySelectorAll(".hd-avatar--lg"))).toHaveLength(1);
  });

  it("shows the singular champion ribbon for a sole winner", () => {
    const wrapper = render(WinnerCard, { props: { name: "Alice", winners: [alice], score: 42 } });
    expect(wrapper.container.querySelector(".winner-card__ribbon")?.textContent).toBe("Champion");
  });

  it("shows the plural ribbon, all names and one avatar per player for a tie", () => {
    const wrapper = render(WinnerCard, { props: { name: "Alice and Bob", winners: [alice, bob], score: 42 } });
    expect(wrapper.container.querySelector(".winner-card__ribbon")?.textContent).toBe("Champions");
    expect(wrapper.container.textContent!).toContain("Alice and Bob");
    expect(Array.from(wrapper.container.querySelectorAll(".hd-avatar--lg")).map((a) => a.textContent!)).toEqual([
      "A",
      "B",
    ]);
  });

  it("crowns nobody when nobody scored", () => {
    const wrapper = render(WinnerCard, { props: { name: "Alice and Bob", winners: [alice, bob], score: 0 } });
    expect(wrapper.container.textContent!).toContain("No winner this time");
    expect(wrapper.container.textContent!).not.toContain("Alice");
    expect(wrapper.container.querySelector(".winner-card__ribbon")! !== null).toBe(false);
    expect(wrapper.container.querySelector(".hd-avatar")! !== null).toBe(false);
  });

  it("contains no emoji", () => {
    const wrapper = render(WinnerCard, { props: { name: "Alice", winners: [alice], score: 42 } });
    expect(EMOJI.test(wrapper.container.textContent!)).toBe(false);
  });
});
