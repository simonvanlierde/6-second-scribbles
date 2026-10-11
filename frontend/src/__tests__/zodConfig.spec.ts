import { describe, expect, it } from "vitest";
import { config } from "zod";

import "@/lib/zodConfig";

describe("zodConfig", () => {
  it("turns off zod's eval probe, which the CSP would block", () => {
    expect(config().jitless).toBe(true);
  });
});
