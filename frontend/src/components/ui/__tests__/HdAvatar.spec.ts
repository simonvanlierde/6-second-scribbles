import { render } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";

import HdAvatar from "@/components/ui/HdAvatar.svelte";

describe("HdAvatar", () => {
  it("renders the initial passed in", () => {
    const w = render(HdAvatar, { props: { initial: "S", color: "var(--avatar-3)" } });
    expect(w.container.textContent?.trim()).toBe("S");
  });

  it("applies the size class", () => {
    const sm = render(HdAvatar, { props: { initial: "X", color: "var(--avatar-1)", size: "sm" } });
    const lg = render(HdAvatar, { props: { initial: "X", color: "var(--avatar-1)", size: "lg" } });
    expect(Array.from(sm.container.firstElementChild?.classList)).toContain("hd-avatar--sm");
    expect(Array.from(lg.container.firstElementChild?.classList)).toContain("hd-avatar--lg");
  });

  it("sets background color via inline style", () => {
    const w = render(HdAvatar, { props: { initial: "S", color: "#FFB4A2" } });
    expect((w.container.firstElementChild! as HTMLElement).style.background).toMatch(/#ffb4a2|rgb\(255, 180, 162\)/i);
  });
});
