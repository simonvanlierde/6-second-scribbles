import { fireEvent, render } from "@testing-library/svelte";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HdInput from "@/components/ui/HdInput.svelte";

describe("HdInput", () => {
  it("renders an input element", () => {
    const w = render(HdInput, { props: { ...callbacks } });
    expect(Boolean(w.container.querySelector("input"))).toBe(true);
  });

  it("supports v-model via update:modelValue", async () => {
    const w = render(HdInput, { props: { ...callbacks, modelValue: "" } });
    await fireEvent.input(w.container.querySelector("input")!, { target: { value: "hello" } });
    expect(events["update:modelValue"].mock.calls?.[0]).toEqual(["hello"]);
  });

  it("renders the placeholder", () => {
    const w = render(HdInput, { props: { ...callbacks, placeholder: "type here" } });
    expect(w.container.querySelector("input")?.getAttribute("placeholder")).toBe("type here");
  });

  it("applies the code variant class", () => {
    const w = render(HdInput, { props: { ...callbacks, variant: "code" } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-input--code");
  });
});

const events = { "update:modelValue": vi.fn() };
const callbacks = { onmodelValueChange: events["update:modelValue"] };
beforeEach(() => {
  for (const event of Object.values(events)) event.mockClear();
});
