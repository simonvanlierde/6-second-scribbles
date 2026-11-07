import { render } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";

import HdTimer from "@/components/ui/HdTimer.svelte";

describe("HdTimer", () => {
  it("renders the seconds value", () => {
    const w = render(HdTimer, { props: { seconds: 42 } });
    expect(w.container.textContent?.trim()).toContain("42");
  });

  it("uses calm style above the urgentAt threshold", () => {
    const w = render(HdTimer, { props: { seconds: 30, urgentAt: 10 } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-timer--calm");
    expect(Array.from(w.container.firstElementChild?.classList)).not.toContain("hd-timer--urgent");
  });

  it("flips to urgent style at or below the urgentAt threshold", () => {
    const w = render(HdTimer, { props: { seconds: 7, urgentAt: 10 } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-timer--urgent");
  });

  it("uses 10s as the default urgent threshold", () => {
    const w = render(HdTimer, { props: { seconds: 9 } });
    expect(Array.from(w.container.firstElementChild?.classList)).toContain("hd-timer--urgent");
  });
});
