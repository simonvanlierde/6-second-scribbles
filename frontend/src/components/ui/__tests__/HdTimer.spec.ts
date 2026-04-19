import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import HdTimer from "@/components/ui/HdTimer.vue";

describe("HdTimer", () => {
  it("renders the seconds value", () => {
    const w = mount(HdTimer, { props: { seconds: 42 } });
    expect(w.text()).toContain("42");
  });

  it("uses calm style above the urgentAt threshold", () => {
    const w = mount(HdTimer, { props: { seconds: 30, urgentAt: 10 } });
    expect(w.classes()).toContain("hd-timer--calm");
    expect(w.classes()).not.toContain("hd-timer--urgent");
  });

  it("flips to urgent style at or below the urgentAt threshold", () => {
    const w = mount(HdTimer, { props: { seconds: 7, urgentAt: 10 } });
    expect(w.classes()).toContain("hd-timer--urgent");
  });

  it("uses 10s as the default urgent threshold", () => {
    const w = mount(HdTimer, { props: { seconds: 9 } });
    expect(w.classes()).toContain("hd-timer--urgent");
  });
});
