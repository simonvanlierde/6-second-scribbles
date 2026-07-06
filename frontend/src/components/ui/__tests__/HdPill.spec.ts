import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdPill from "@/components/ui/HdPill.vue";

describe("HdPill", () => {
  it("renders default slot", () => {
    const w = mount(HdPill, { slots: { default: "ready" } });
    expect(w.text()).toBe("ready");
  });

  it("applies the default variant class", () => {
    const w = mount(HdPill, { slots: { default: "x" } });
    expect(w.classes()).toContain("hd-pill--default");
  });

  it("applies the info variant class", () => {
    const w = mount(HdPill, {
      props: { variant: "info" },
      slots: { default: "x" },
    });
    expect(w.classes()).toContain("hd-pill--info");
  });

  it("applies the success variant class", () => {
    const w = mount(HdPill, {
      props: { variant: "success" },
      slots: { default: "x" },
    });
    expect(w.classes()).toContain("hd-pill--success");
  });
});
