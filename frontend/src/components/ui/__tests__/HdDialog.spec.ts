import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdDialog from "@/components/ui/HdDialog.svelte";

describe("HdDialog", () => {
  it("renders title and message", () => {
    const w = render(HdDialog, {
      props: { ...callbacks, open: true, title: "Are you sure?", message: "This will leave the room." },
    });
    expect(w.container.textContent?.trim()).toContain("Are you sure?");
    expect(w.container.textContent?.trim()).toContain("This will leave the room.");
  });

  it("emits confirm when the confirm button is clicked", async () => {
    const w = render(HdDialog, { props: { ...callbacks, open: true, title: "T", message: "M" } });
    await fireEvent.click(w.container.querySelector('[data-testid="hd-dialog-confirm"]')!);
    expect(events.confirm.mock.calls).toHaveLength(1);
    expect(w.container.querySelector("dialog")?.open).toBe(false);
  });

  it("emits cancel when the cancel button is clicked", async () => {
    const w = render(HdDialog, {
      props: { ...callbacks, open: true, title: "T", message: "M", cancelLabel: "Cancel" },
    });
    await fireEvent.click(w.container.querySelector('[data-testid="hd-dialog-cancel"]')!);
    expect(events.cancel.mock.calls).toHaveLength(1);
    expect(w.container.querySelector("dialog")?.open).toBe(false);
  });

  it("uses custom button labels when provided", () => {
    const w = render(HdDialog, {
      props: { ...callbacks, open: true, title: "T", message: "M", confirmLabel: "Yep", cancelLabel: "Nope" },
    });
    expect(w.container.querySelector('[data-testid="hd-dialog-confirm"]')?.textContent?.trim()).toBe("Yep");
    expect(w.container.querySelector('[data-testid="hd-dialog-cancel"]')?.textContent?.trim()).toBe("Nope");
  });

  it("can carry its own close button and no action buttons", async () => {
    const w = render(HdDialog, {
      props: { ...callbacks, open: true, title: "Settings", closeLabel: "Close", actions: false },
    });
    expect(Boolean(w.container.querySelector('[data-testid="hd-dialog-confirm"]'))).toBe(false);
    const close = w.container.querySelector('[data-testid="hd-dialog-close"]');
    expect(close?.getAttribute("aria-label")).toBe("Close");
    await fireEvent.click(close!);
    expect(events.cancel.mock.calls).toHaveLength(1);
    expect(w.container.querySelector("dialog")?.open).toBe(false);
  });
});

const events = { confirm: vi.fn(), cancel: vi.fn() };
const callbacks = { onconfirm: events.confirm, oncancel: events.cancel };
beforeEach(() => {
  for (const event of Object.values(events)) event.mockClear();
});
