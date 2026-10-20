import { describe, expect, it } from "vitest";

import en from "@/locales/en.json";

const locales = import.meta.glob<Record<string, unknown>>("../locales/*.json", { eager: true, import: "default" });

function keyPaths(node: unknown, prefix = ""): string[] {
  if (typeof node !== "object" || node === null) return [prefix];
  return Object.entries(node).flatMap(([key, value]) => keyPaths(value, prefix ? `${prefix}.${key}` : key));
}

const byName = (a: string, b: string) => a.localeCompare(b);
const enKeys = keyPaths(en).sort(byName);

describe("locale key parity", () => {
  it.each(Object.entries(locales))("%s has exactly the keys of en.json", (_path, messages) => {
    expect(keyPaths(messages).sort(byName)).toEqual(enKeys);
  });
});
