// cspell:ignore dans joueur joueurs salon gracz gracze graczy pokoju punkt punkty sekund sekunda sekundy Została Zostało Zostały
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

describe("plurals", () => {
  afterEach(async () => {
    await setLocale("en");
  });

  const players = (count: number) => i18n.global.t("roomEntry.playersInRoom", { count });

  it("uses the three Polish forms: 1, 2-4 (not 12-14), and the rest", async () => {
    await setLocale("pl");
    expect([0, 1, 2, 5, 12, 22, 25].map(players)).toEqual([
      "0 graczy w pokoju",
      "1 gracz w pokoju",
      "2 gracze w pokoju",
      "5 graczy w pokoju",
      "12 graczy w pokoju",
      "22 gracze w pokoju",
      "25 graczy w pokoju",
    ]);
  });

  it("declines the Polish time-left announcement too", async () => {
    await setLocale("pl");
    const left = (count: number) => i18n.global.t("phase.timeLow", { count });
    expect([10, 3, 1].map(left)).toEqual(["Zostało 10 sekund", "Zostały 3 sekundy", "Została 1 sekunda"]);
  });

  it("counts zero in the French singular", async () => {
    await setLocale("fr");
    expect([0, 1, 2].map(players)).toEqual([
      "0 joueur dans le salon",
      "1 joueur dans le salon",
      "2 joueurs dans le salon",
    ]);
  });

  it("keeps the two English forms", () => {
    expect([0, 1, 2].map(players)).toEqual(["0 players in room", "1 player in room", "2 players in room"]);
  });

  it("still picks singular and plural when a Polish string has only two forms", async () => {
    await setLocale("pl");
    i18n.global.mergeLocaleMessage("pl", { twoFormTest: "{count} punkt | {count} punkty" });
    const points = (count: number) => i18n.global.t("twoFormTest", { count });
    expect([1, 2, 5].map(points)).toEqual(["1 punkt", "2 punkty", "5 punkty"]);
  });
});
