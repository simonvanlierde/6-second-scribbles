import { fireEvent, render } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdButton from "@/components/ui/HdButton.svelte";

describe("HdButton", () => {
  it("renders default slot text", () => {
    const w = render(HdButton, { props: { ...callbacks, children: text("Click me") } });
    expect(w.container.textContent?.trim()).toBe("Click me");
  });

  it("emits click when pressed", async () => {
    const w = render(HdButton, { props: { ...callbacks, children: text("Go") } });
    await fireEvent.click(w.container.firstElementChild!);
    expect(events.click.mock.calls.length ? events.click.mock.calls : undefined).toHaveLength(1);
  });

  it("does not emit click when disabled", async () => {
    const w = render(HdButton, { props: { ...callbacks, disabled: true, children: text("Go") } });
    (w.container.firstElementChild as HTMLButtonElement).click();
    expect(events.click).not.toHaveBeenCalled();
  });

  it("applies the variant class", () => {
    const primary = render(HdButton, { props: { ...callbacks, variant: "primary", children: text("P") } });
    const secondary = render(HdButton, { props: { ...callbacks, variant: "secondary", children: text("S") } });
    expect(Array.from(primary.container.firstElementChild?.classList)).toContain("hd-btn--primary");
    expect(Array.from(secondary.container.firstElementChild?.classList)).toContain("hd-btn--secondary");
  });

  it("renders as <button type='button'> by default", () => {
    const w = render(HdButton, { props: { ...callbacks, children: text("X") } });
    expect(w.container.firstElementChild?.tagName).toBe("BUTTON");
    expect(w.container.firstElementChild?.getAttribute("type")).toBe("button");
  });
});

function text(value: string) {
  return createRawSnippet(() => ({ render: () => `<span>${value}</span>` }));
}

const events = { click: vi.fn() };
const callbacks = { onclick: events.click };
beforeEach(() => {
  for (const event of Object.values(events)) event.mockClear();
});
