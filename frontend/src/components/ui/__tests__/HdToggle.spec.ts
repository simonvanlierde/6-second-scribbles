import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdToggle from "@/components/ui/HdToggle.svelte";

describe("HdToggle", () => {
  it("renders optional label and help text", () => {
    const wrapper = render(HdToggle, {
      props: {
        ...callbacks,
        modelValue: false,
        label: "Private Room",
        help: "Private rooms do not appear in quick play.",
      },
    });

    expect(wrapper.container.textContent?.trim()).toContain("Private Room");
    expect(wrapper.container.querySelector('[role="img"]')?.getAttribute("title")).toBe(
      "Private rooms do not appear in quick play.",
    );
  });

  it("emits model update and change when toggled", async () => {
    const wrapper = render(HdToggle, { props: { ...callbacks, modelValue: false, label: "Private Room" } });

    await fireEvent.click(wrapper.container.querySelector("input")!);

    expect(events["update:modelValue"].mock.calls?.[0]).toEqual([true]);
    expect(events.change.mock.calls).toHaveLength(1);
  });
});

const events = { "update:modelValue": vi.fn(), change: vi.fn() };
const callbacks = { onmodelValueChange: events["update:modelValue"], onchange: events.change };
beforeEach(() => {
  for (const event of Object.values(events)) event.mockClear();
});
