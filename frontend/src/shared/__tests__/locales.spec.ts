import { describe, expect, it } from "vitest";

import { getBrowserLocale } from "@/shared/locales";

describe("getBrowserLocale", () => {
  it.each([
    ["en-US", "en"],
    ["pt-BR", "pt"],
    ["DE", "de"],
    ["zh", "zh-CN"],
    ["zh-CN", "zh-CN"],
    ["zh-Hans-SG", "zh-CN"],
    ["zh-TW", "zh-TW"],
    ["zh-HK", "zh-TW"],
    ["zh-Hant", "zh-TW"],
    ["", "en"],
  ])("maps %j to %s", (tag, expected) => {
    expect(getBrowserLocale(tag)).toBe(expected);
  });
});
