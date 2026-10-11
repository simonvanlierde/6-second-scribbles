import { afterEach, describe, expect, it } from "vitest";

import { i18n, setLocale } from "@/i18n";

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
