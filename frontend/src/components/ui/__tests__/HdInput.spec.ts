import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdInput from "@/components/ui/HdInput.vue";

describe("HdInput", () => {
  it("renders an input element", () => {
    const w = mount(HdInput);
    expect(w.find("input").exists()).toBe(true);
  });

  it("supports v-model via update:modelValue", async () => {
    const w = mount(HdInput, { props: { modelValue: "" } });
    await w.find("input").setValue("hello");
    expect(w.emitted("update:modelValue")?.[0]).toEqual(["hello"]);
  });

  it("renders the placeholder", () => {
    const w = mount(HdInput, { props: { placeholder: "type here" } });
    expect(w.find("input").attributes("placeholder")).toBe("type here");
  });

  it("applies the code variant class", () => {
    const w = mount(HdInput, { props: { variant: "code" } });
    expect(w.classes()).toContain("hd-input--code");
  });
});
