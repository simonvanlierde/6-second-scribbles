import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdSegmented from "@/components/ui/HdSegmented.vue";

const options = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "auto", label: "Auto" },
];

describe("HdSegmented", () => {
  it("renders one radio input per option with a visible label", () => {
    const w = mount(HdSegmented, { props: { modelValue: "light", options } });
    expect(w.findAll('input[type="radio"]')).toHaveLength(3);
    expect(w.text()).toContain("Light");
    expect(w.text()).toContain("Dark");
    expect(w.text()).toContain("Auto");
  });

  it("checks the radio matching modelValue", () => {
    const w = mount(HdSegmented, { props: { modelValue: "dark", options } });
    const radios = w.findAll('input[type="radio"]');
    expect((radios[0]?.element as HTMLInputElement).checked).toBe(false);
    expect((radios[1]?.element as HTMLInputElement).checked).toBe(true);
  });

  it("emits update:modelValue when a different option is selected", async () => {
    const w = mount(HdSegmented, { props: { modelValue: "light", options } });
    await w.findAll('input[type="radio"]')[2]?.setValue(true);
    expect(w.emitted("update:modelValue")?.[0]).toEqual(["auto"]);
  });

  it("groups the radios under a single name so only one is selected at a time", () => {
    const w = mount(HdSegmented, {
      props: { modelValue: "light", options, name: "theme" },
    });
    for (const r of w.findAll('input[type="radio"]')) {
      expect(r.attributes("name")).toBe("theme");
    }
  });
});
