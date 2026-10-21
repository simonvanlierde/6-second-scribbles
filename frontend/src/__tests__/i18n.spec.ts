import { afterEach, describe, expect, it } from "vitest";

import { i18n, setLocale } from "@/i18n";
import en from "@/locales/en.json";
import { SUPPORTED_LOCALES } from "@/shared/locales";

const localeFiles = import.meta.glob<{ default: Record<string, unknown> }>("@/locales/*.json", { eager: true });

function flatKeys(messages: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(messages).flatMap(([key, value]) =>
    value && typeof value === "object"
      ? flatKeys(value as Record<string, unknown>, `${prefix}${key}.`)
      : [`${prefix}${key}`],
  );
}

describe("locale files", () => {
  const enKeys = flatKeys(en);

  it.each(SUPPORTED_LOCALES.filter((l) => l !== "en"))("%s has exactly the keys in en.json", (locale) => {
    const file = Object.entries(localeFiles).find(([path]) => path.endsWith(`/${locale}.json`));
    expect(file, `missing locales/${locale}.json`).toBeDefined();
    const keys = new Set(flatKeys(file?.[1].default ?? {}));
    expect(
      enKeys.filter((key) => !keys.has(key)),
      "missing keys",
    ).toEqual([]);
    // A key en.json dropped but a locale still carries is dead text nobody maintains.
    expect(
      [...keys].filter((key) => !enKeys.includes(key)),
      "keys en.json no longer has",
    ).toEqual([]);
  });
});

describe("setLocale", () => {
  afterEach(async () => {
    await setLocale("en");
  });

  it("sets the document language to the chosen locale", async () => {
    await setLocale("de");
    expect(i18n.global.locale.value).toBe("de");
    expect(document.documentElement.lang).toBe("de");
  });

  it("leaves the document language alone for an unsupported locale", async () => {
    await setLocale("fr");
    await setLocale("xx");
    expect(document.documentElement.lang).toBe("fr");
  });
});
