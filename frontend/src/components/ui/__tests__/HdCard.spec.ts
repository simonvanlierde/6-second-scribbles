import { render } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { describe, expect, it, vi } from "vitest";

import HdCard from "@/components/ui/HdCard.svelte";

describe("HdCard", () => {
  it("renders default slot", () => {
    const w = render(HdCard, { props: { children: text("<p>hi</p>") } });
    expect(w.container.textContent?.trim()).toBe("hi");
  });

  it("applies the default variant class", () => {
    const w = render(HdCard, { props: { children: text("x") } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-card--default");
  });

  it("applies the postit variant class", () => {
    const w = render(HdCard, { props: { variant: "postit", children: text("x") } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-card--postit");
  });
});

function text(value: string) {
  return createRawSnippet(() => ({ render: () => `<span>${value}</span>` }));
}
