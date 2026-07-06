import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdIconButton from "@/components/ui/HdIconButton.vue";

describe("HdIconButton", () => {
  it("renders a button with the label as aria-label", () => {
    const w = mount(HdIconButton, {
      props: { label: "Settings" },
      slots: { default: "⚙" },
    });
    expect(w.element.tagName).toBe("BUTTON");
    expect(w.attributes("aria-label")).toBe("Settings");
    expect(w.attributes("type")).toBe("button");
  });

  it("renders the slotted icon content", () => {
    const w = mount(HdIconButton, {
      props: { label: "Close" },
      slots: { default: "<svg data-testid='x'></svg>" },
    });
    expect(w.find("[data-testid='x']").exists()).toBe(true);
  });

  it("emits click when pressed and not disabled", async () => {
    const w = mount(HdIconButton, {
      props: { label: "X" },
      slots: { default: "x" },
    });
    await w.trigger("click");
    expect(w.emitted("click")).toHaveLength(1);
  });

  it("does not emit click when disabled", async () => {
    const w = mount(HdIconButton, {
      props: { label: "X", disabled: true },
      slots: { default: "x" },
    });
    await w.trigger("click");
    expect(w.emitted("click")).toBeUndefined();
  });

  it("applies the ghost variant class", () => {
    const w = mount(HdIconButton, {
      props: { label: "X", variant: "ghost" },
      slots: { default: "x" },
    });
    expect(w.classes()).toContain("hd-icon-btn--ghost");
  });
});
