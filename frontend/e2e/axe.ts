import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

// WCAG 2.1 A/AA rule tags. axe checks against these specific rules — it does
// not certify conformance, it flags violations of them.
const WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

export async function expectNoViolations(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG_TAGS).analyze();
  // Map to id + help so a failure names the rule and count, not just "[]".
  expect(violations.map((v) => `${v.id} (${v.nodes.length}): ${v.help}`)).toEqual([]);
}
