import { beforeEach, describe, expect, it, vi } from "vitest";

import { useLocaleAvailability } from "@/composables/useLocaleAvailability";

const apiRequestMock = vi.fn();

vi.mock("@/lib/api", () => ({
  apiRequest: (...args: unknown[]) => apiRequestMock(...args),
}));

describe("useLocaleAvailability", () => {
  beforeEach(() => {
    apiRequestMock.mockReset();
  });

  it("keeps locales enabled before first successful load", () => {
    const { localeOptions } = useLocaleAvailability();

    expect(localeOptions.value.every((option) => option.enabled)).toBe(true);
  });

  it("disables locales with zero category coverage after load", async () => {
    apiRequestMock.mockResolvedValueOnce([
      {
        locale: "en",
        category_count: 5,
        difficulty_counts: { easy: 2, medium: 2, hard: 1 },
      },
      { locale: "es", category_count: 0, difficulty_counts: {} },
    ]);

    const { localeOptions, fetchLocaleAvailability } = useLocaleAvailability();
    await fetchLocaleAvailability(true);

    const en = localeOptions.value.find((option) => option.code === "en");
    const es = localeOptions.value.find((option) => option.code === "es");
    const fr = localeOptions.value.find((option) => option.code === "fr");

    expect(en?.enabled).toBe(true);
    expect(es?.enabled).toBe(false);
    expect(es?.reason).toContain("No playable categories yet");
    expect(fr?.enabled).toBe(false);
  });

  it("uses backend playable locale codes for room language availability", async () => {
    apiRequestMock.mockResolvedValueOnce([
      {
        locale: "de",
        category_count: 37,
        difficulty_counts: { easy: 12, medium: 12, hard: 13 },
      },
      {
        locale: "zh-CN",
        category_count: 37,
        difficulty_counts: { easy: 12, medium: 12, hard: 13 },
      },
      {
        locale: "zh-TW",
        category_count: 37,
        difficulty_counts: { easy: 12, medium: 12, hard: 13 },
      },
    ]);

    const { localeOptions, fetchLocaleAvailability } = useLocaleAvailability();
    await fetchLocaleAvailability(true);

    expect(localeOptions.value.some((option) => option.code === "zh")).toBe(false);
    expect(localeOptions.value.find((option) => option.code === "de")?.enabled).toBe(true);
    expect(localeOptions.value.find((option) => option.code === "zh-CN")?.enabled).toBe(true);
    expect(localeOptions.value.find((option) => option.code === "zh-TW")?.enabled).toBe(true);
  });
});
