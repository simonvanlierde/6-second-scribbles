import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

type E2EPage = Parameters<Parameters<typeof test>[1]>[0]["page"];

// WCAG 2.1 A/AA rule tags. axe checks against these specific rules — it does
// not certify conformance, it flags violations of them.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function expectNoViolations(page: E2EPage) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  // Map to id + help so a failure names the rule and count, not just "[]".
  expect(violations.map((v) => `${v.id} (${v.nodes.length}): ${v.help}`)).toEqual([]);
}

// Frontend-only screens (no backend needed): Home, the Settings panel, and the
// design-system page, which renders the full component library (buttons, timer,
// toast, avatars, badges, cards). Each is scanned in both colour schemes since
// contrast differs between them. In-room screens reuse these same components.
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
