import { type Browser, expect, type Locator, type Page, test } from "@playwright/test";

// An iPhone 12-14 screen. 44 px is the smallest touch target Apple and WCAG 2.5.5 ask for.
const PHONE = { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true };
const MIN_TARGET = 44;

async function openPlayer(browser: Browser, name: string): Promise<Page> {
  const page = await (await browser.newContext(PHONE)).newPage();
  await page.goto("/");
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
  return page;
}

async function expectTarget(locator: Locator) {
  const box = await locator.boundingBox();
  if (!box) throw new Error("Expected a visible touch target");
  expect(Math.round(box.width)).toBeGreaterThanOrEqual(MIN_TARGET);
  expect(Math.round(box.height)).toBeGreaterThanOrEqual(MIN_TARGET);
}

test("touch targets are 44 px and Finish stays on a phone screen", async ({ browser }) => {
  test.setTimeout(60_000);
  const host = await openPlayer(browser, "Host");
  await host.getByRole("button", { name: /create room/i }).click();
  await expect(host).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  const roomCode = host.url().split("/rooms/")[1] ?? "";

  const guest = await openPlayer(browser, "Guest");
  await guest.locator("input.hd-input--code").fill(roomCode);
  await guest.getByRole("button", { name: /join room/i }).click();
  await expect(host.getByRole("heading", { name: /players \(2\)/i })).toBeVisible();

  await expectTarget(host.getByRole("button", { name: /^kick player$/i }));
  await expectTarget(host.locator(".advanced-toggle"));
  await host.locator(".advanced-toggle").click();
  for (const button of await host.locator(".stepper__btn").all()) await expectTarget(button);

  // The lobby doodle swatches stay 38 px to fit one row; a pseudo-element widens what a tap hits.
  const swatch = host.locator(".toolbar--compact .swatch").nth(1);
  await swatch.scrollIntoViewIfNeeded();
  const box = await swatch.boundingBox();
  if (!box) throw new Error("Expected the lobby doodle swatches");
  await host.mouse.click(box.x + box.width / 2, box.y - 2);
  await expect(swatch).toHaveClass(/swatch--active/);

  await host.getByRole("button", { name: /start game/i }).click();
  const finish = host.getByRole("button", { name: /^finish$/i });
  await expect(finish).toBeInViewport({ ratio: 1 });
});
