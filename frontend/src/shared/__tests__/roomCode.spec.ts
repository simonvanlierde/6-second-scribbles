import { describe, expect, it } from "vitest";

import { isValidRoomCode, normalizeRoomCode, ROOM_CODE_LENGTH } from "@/shared/roomCode";

describe("normalizeRoomCode", () => {
  it("trims and uppercases", () => {
    expect(normalizeRoomCode("  ab12cd  ")).toBe("AB12CD");
  });

  it("handles empty/whitespace input", () => {
    expect(normalizeRoomCode("   ")).toBe("");
  });
});

describe("isValidRoomCode", () => {
  it("accepts a normalized code of the expected length", () => {
    expect(isValidRoomCode("abc123")).toBe(true);
    expect(isValidRoomCode("ABC123")).toBe(true);
  });

  it("rejects wrong length or illegal characters", () => {
    expect(isValidRoomCode("abc12")).toBe(false);
    expect(isValidRoomCode("abc1234")).toBe(false);
    expect(isValidRoomCode("abc-12")).toBe(false);
    expect(isValidRoomCode("a".repeat(ROOM_CODE_LENGTH - 1))).toBe(false);
  });
});
