import { expect, test } from "@playwright/test";

import { expectNoViolations } from "./axe";

// Frontend-only screens (no backend needed): Home, the Settings panel, and the
// design-system page, which renders the full component library (buttons, timer,
// toast, avatars, badges, cards). Each is scanned in both colour schemes since
// contrast differs between them. The in-room screens are in a11y-game.spec.ts,
// which needs the backend.
for (const scheme of ["light", "dark"] as const) {
  test.describe(`Accessibility (axe) — ${scheme}`, () => {
    test.use({ colorScheme: scheme });

    test("Home has no WCAG A/AA violations", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
      await expectNoViolations(page);
    });

    test("Settings panel has no WCAG A/AA violations", async ({ page }) => {
      await page.goto("/");
      await page.getByRole("button", { name: /^settings$/i }).click();
      await expect(page.getByPlaceholder(/pick a name/i)).toBeVisible();
      await expectNoViolations(page);
    });

    test("Component library has no WCAG A/AA violations", async ({ page }) => {
      await page.goto("/__ds");
      await expect(page.getByRole("heading", { name: /avatars/i })).toBeVisible();
      await expectNoViolations(page);
    });
  });
}

// One non-English pass: translated strings change label lengths and the page
// language, which axe checks (html-has-lang, valid-lang).
test.describe("Accessibility (axe) — German", () => {
  test.use({ locale: "de-DE" });

  test("Home has no WCAG A/AA violations and lang follows the locale", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "de");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
    await expectNoViolations(page);
  });
});
