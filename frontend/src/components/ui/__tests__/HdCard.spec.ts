import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdCard from "@/components/ui/HdCard.vue";

describe("HdCard", () => {
  it("renders default slot", () => {
    const w = mount(HdCard, { slots: { default: "<p>hi</p>" } });
    expect(w.text()).toBe("hi");
  });

  it("applies the default variant class", () => {
    const w = mount(HdCard, { slots: { default: "x" } });
    expect(w.classes()).toContain("hd-card--default");
  });

  it("applies the postit variant class", () => {
    const w = mount(HdCard, {
      props: { variant: "postit" },
      slots: { default: "x" },
    });
    expect(w.classes()).toContain("hd-card--postit");
  });
});
