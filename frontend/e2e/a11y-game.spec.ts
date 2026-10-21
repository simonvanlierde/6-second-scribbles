import { type Browser, expect, type Page, test } from "@playwright/test";

import { expectNoViolations } from "./axe";

// The in-room screens, which need the backend: kept out of a11y.spec.ts, whose CI
// job (playwright.a11y.config.ts) runs the frontend alone.

async function openPlayer(browser: Browser, name: string, colorScheme: "light" | "dark"): Promise<Page> {
  const page = await (await browser.newContext({ colorScheme })).newPage();
  await page.goto("/");
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
  return page;
}

// One game per colour scheme, scanned at each screen as both players reach it.
for (const scheme of ["light", "dark"] as const) {
  test(`game screens have no WCAG A/AA violations — ${scheme}`, async ({ browser }) => {
    test.setTimeout(90_000);
    const host = await openPlayer(browser, "Host", scheme);
    await host.getByRole("button", { name: /create room/i }).click();
    await expect(host).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
    const roomCode = host.url().split("/rooms/")[1] ?? "";

    const guest = await openPlayer(browser, "Guest", scheme);
    await guest.locator("input.hd-input--code").fill(roomCode);
    await guest.getByRole("button", { name: /join room/i }).click();
    await expect(host.getByRole("heading", { name: /players \(2\)/i })).toBeVisible();

    await test.step("lobby", async () => {
      await expectNoViolations(host);
      await expectNoViolations(guest);
    });

    await host.getByRole("button", { name: /start game/i }).click();
    await test.step("drawing", async () => {
      for (const page of [host, guest]) {
        await expect(page.getByRole("button", { name: /^finish$/i }).first()).toBeVisible({ timeout: 10_000 });
        await expectNoViolations(page);
      }
    });

    for (const page of [host, guest]) {
      await page
        .getByRole("button", { name: /^finish$/i })
        .first()
        .click();
    }
    await test.step("guessing", async () => {
      for (const page of [host, guest]) {
        await expect(page.getByRole("button", { name: /submit guesses/i })).toBeVisible({ timeout: 15_000 });
        await expectNoViolations(page);
      }
    });

    for (const page of [host, guest]) {
      await page.getByRole("textbox", { name: /guess 1/i }).fill("cat");
      await page.getByRole("button", { name: /submit guesses/i }).click();
    }
    await test.step("results", async () => {
      for (const page of [host, guest]) {
        await expect(page.getByRole("heading", { name: /round 1 results/i })).toBeVisible({ timeout: 15_000 });
        await expectNoViolations(page);
      }
    });
  });
}
