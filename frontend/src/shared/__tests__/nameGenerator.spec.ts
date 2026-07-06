import { afterEach, describe, expect, it, vi } from "vitest";

import { generateRandomName } from "@/shared/nameGenerator";

describe("generateRandomName", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("combines one adjective and one noun", () => {
    vi.spyOn(Math, "random").mockReturnValue(0);

    expect(generateRandomName()).toBe("Swift Panda");
  });
});
