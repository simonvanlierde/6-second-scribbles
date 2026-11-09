import { fireEvent, render } from "@testing-library/svelte";
import { createRawSnippet } from "svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdIconButton from "@/components/ui/HdIconButton.svelte";

describe("HdIconButton", () => {
  it("renders a button with the label as aria-label", () => {
    const w = render(HdIconButton, { props: { ...callbacks, label: "Settings", children: text("⚙") } });
    expect(w.container.firstElementChild?.tagName).toBe("BUTTON");
    expect(w.container.firstElementChild?.getAttribute("aria-label")).toBe("Settings");
    expect(w.container.firstElementChild?.getAttribute("type")).toBe("button");
  });

  it("renders the slotted icon content", () => {
    const w = render(HdIconButton, {
      props: { ...callbacks, label: "Close", children: text("<svg data-testid='x'></svg>") },
    });
    expect(Boolean(w.container.querySelector("[data-testid='x']"))).toBe(true);
  });

  it("emits click when pressed and not disabled", async () => {
    const w = render(HdIconButton, { props: { ...callbacks, label: "X", children: text("x") } });
    await fireEvent.click(w.container.firstElementChild!);
    expect(events.click.mock.calls.length ? events.click.mock.calls : undefined).toHaveLength(1);
  });

  it("does not emit click when disabled", async () => {
    const w = render(HdIconButton, { props: { ...callbacks, label: "X", disabled: true, children: text("x") } });
    (w.container.firstElementChild as HTMLButtonElement).click();
    expect(events.click).not.toHaveBeenCalled();
  });

  it("applies the ghost variant class", () => {
    const w = render(HdIconButton, { props: { ...callbacks, label: "X", variant: "ghost", children: text("x") } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-icon-btn--ghost");
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
