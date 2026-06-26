import { describe, expect, it } from "vitest";

import { ALLOWED_CHARS, generateRoomCode } from "@/shared/roomCode";

describe("generateRoomCode", () => {
  it("returns a string of the default length (6)", () => {
    expect(generateRoomCode()).toHaveLength(6);
  });

  it("returns a string of a custom length", () => {
    expect(generateRoomCode(4)).toHaveLength(4);
    expect(generateRoomCode(10)).toHaveLength(10);
  });

  it("only contains characters from ALLOWED_CHARS", () => {
    const allowed = new Set(ALLOWED_CHARS.split(""));
    const code = generateRoomCode(100);
    for (const char of code) {
      expect(allowed.has(char), `unexpected character: ${char}`).toBe(true);
    }
  });

  it("produces different codes on repeated calls (probabilistic)", () => {
    const codes = new Set(Array.from({ length: 20 }, () => generateRoomCode()));
    // With 36^6 ≈ 2.18 billion possibilities, 20 calls should never collide
    expect(codes.size).toBeGreaterThan(1);
  });

  it("ALLOWED_CHARS contains only uppercase letters and digits", () => {
    expect(ALLOWED_CHARS).toMatch(/^[A-Z0-9]+$/);
  });
});
