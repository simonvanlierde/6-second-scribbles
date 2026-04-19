import { describe, expect, it } from "vitest";

import { AVATAR_COLORS, getAvatarColor, getAvatarInitial } from "@/composables/useAvatar";

describe("useAvatar", () => {
  it("exposes 6 token colors", () => {
    expect(AVATAR_COLORS).toHaveLength(6);
    for (const c of AVATAR_COLORS) {
      expect(c).toMatch(/^var\(--avatar-\d\)$/);
    }
  });

  it("returns a deterministic color for the same player id", () => {
    const a = getAvatarColor("player-abc-123");
    const b = getAvatarColor("player-abc-123");
    expect(a).toBe(b);
    expect(AVATAR_COLORS).toContain(a);
  });

  it("returns different colors for different ids most of the time", () => {
    const set = new Set(["a", "b", "c", "d", "e", "f"].map(getAvatarColor));
    expect(set.size).toBeGreaterThan(1);
  });

  it("returns the uppercased first non-whitespace character of a name", () => {
    expect(getAvatarInitial("simon")).toBe("S");
    expect(getAvatarInitial("  jules ")).toBe("J");
  });

  it("returns ? for an empty name", () => {
    expect(getAvatarInitial("")).toBe("?");
    expect(getAvatarInitial("   ")).toBe("?");
  });
});
