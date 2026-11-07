import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdSegmented from "@/components/ui/HdSegmented.svelte";

const options = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "auto", label: "Auto" },
];

describe("HdSegmented", () => {
  it("renders one radio input per option with a visible label", () => {
    const w = render(HdSegmented, { props: { ...callbacks, modelValue: "light", options } });
    expect(Array.from(w.container.querySelectorAll('input[type="radio"]'))).toHaveLength(3);
    expect(w.container.textContent?.trim()).toContain("Light");
    expect(w.container.textContent?.trim()).toContain("Dark");
    expect(w.container.textContent?.trim()).toContain("Auto");
  });

  it("checks the radio matching modelValue", () => {
    const w = render(HdSegmented, { props: { ...callbacks, modelValue: "dark", options } });
    const radios = Array.from(w.container.querySelectorAll('input[type="radio"]'));
    expect((radios[0] as HTMLInputElement | undefined)?.checked).toBe(false);
    expect((radios[1] as HTMLInputElement | undefined)?.checked).toBe(true);
  });

  it("emits update:modelValue when a different option is selected", async () => {
    const w = render(HdSegmented, { props: { ...callbacks, modelValue: "light", options } });
    await fireEvent.click(w.container.querySelectorAll('input[type="radio"]')[2]!);
    expect(events["update:modelValue"].mock.calls?.[0]).toEqual(["auto"]);
  });

  it("groups the radios under a single name so only one is selected at a time", () => {
    const w = render(HdSegmented, { props: { ...callbacks, modelValue: "light", options, name: "theme" } });
    for (const r of Array.from(w.container.querySelectorAll('input[type="radio"]'))) {
      expect(r.getAttribute("name")).toBe("theme");
    }
  });
});

const events = { "update:modelValue": vi.fn() };
const callbacks = { onmodelValueChange: events["update:modelValue"] };
beforeEach(() => {
  for (const event of Object.values(events)) event.mockClear();
});
