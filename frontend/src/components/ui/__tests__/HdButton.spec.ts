import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdButton from "@/components/ui/HdButton.vue";

describe("HdButton", () => {
  it("renders default slot text", () => {
    const w = mount(HdButton, { slots: { default: "Click me" } });
    expect(w.text()).toBe("Click me");
  });

  it("emits click when pressed", async () => {
    const w = mount(HdButton, { slots: { default: "Go" } });
    await w.trigger("click");
    expect(w.emitted("click")).toHaveLength(1);
  });

  it("does not emit click when disabled", async () => {
    const w = mount(HdButton, { props: { disabled: true }, slots: { default: "Go" } });
    await w.trigger("click");
    expect(w.emitted("click")).toBeUndefined();
  });

  it("applies the variant class", () => {
    const primary = mount(HdButton, { props: { variant: "primary" }, slots: { default: "P" } });
    const secondary = mount(HdButton, { props: { variant: "secondary" }, slots: { default: "S" } });
    expect(primary.classes()).toContain("hd-btn--primary");
    expect(secondary.classes()).toContain("hd-btn--secondary");
  });

  it("renders as <button type='button'> by default", () => {
    const w = mount(HdButton, { slots: { default: "X" } });
    expect(w.element.tagName).toBe("BUTTON");
    expect(w.attributes("type")).toBe("button");
  });
});
