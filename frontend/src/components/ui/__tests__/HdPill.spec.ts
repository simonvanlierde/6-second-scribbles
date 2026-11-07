import { render } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { describe, expect, it, vi } from "vitest";

import HdPill from "@/components/ui/HdPill.svelte";

describe("HdPill", () => {
  it("renders default slot", () => {
    const w = render(HdPill, { props: { children: text("ready") } });
    expect(w.container.textContent?.trim()).toBe("ready");
  });

  it("applies the default variant class", () => {
    const w = render(HdPill, { props: { children: text("x") } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-pill--default");
  });

  it("applies the info variant class", () => {
    const w = render(HdPill, { props: { variant: "info", children: text("x") } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-pill--info");
  });

  it("applies the success variant class", () => {
    const w = render(HdPill, { props: { variant: "success", children: text("x") } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-pill--success");
  });
});

function text(value: string) {
  return createRawSnippet(() => ({ render: () => `<span>${value}</span>` }));
}
