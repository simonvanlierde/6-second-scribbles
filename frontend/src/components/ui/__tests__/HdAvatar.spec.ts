import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdAvatar from "@/components/ui/HdAvatar.vue";

describe("HdAvatar", () => {
  it("renders the initial passed in", () => {
    const w = mount(HdAvatar, { props: { initial: "S", color: "var(--avatar-3)" } });
    expect(w.text()).toBe("S");
  });

  it("applies the size class", () => {
    const sm = mount(HdAvatar, { props: { initial: "X", color: "var(--avatar-1)", size: "sm" } });
    const lg = mount(HdAvatar, { props: { initial: "X", color: "var(--avatar-1)", size: "lg" } });
    expect(sm.classes()).toContain("hd-avatar--sm");
    expect(lg.classes()).toContain("hd-avatar--lg");
  });

  it("sets background color via inline style", () => {
    const w = mount(HdAvatar, { props: { initial: "S", color: "#FFB4A2" } });
    expect(w.attributes("style")).toContain("background");
    expect(w.attributes("style")).toContain("#FFB4A2".toLowerCase());
  });
});
