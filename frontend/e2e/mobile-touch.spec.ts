import { type Browser, type BrowserContextOptions, expect, type Locator, type Page, test } from "@playwright/test";

// An iPhone 12-14 screen. 44 px is the smallest touch target Apple and WCAG 2.5.5 ask for.
const PHONE = { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true };
// A short laptop window, where the word card fills the sidebar.
const LAPTOP = { viewport: { width: 1280, height: 720 } };
const MIN_TARGET = 44;

async function openPlayer(browser: Browser, name: string, options: BrowserContextOptions): Promise<Page> {
  const page = await (await browser.newContext(options)).newPage();
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

/** Opens a room with a host and a guest, and returns the host's page in the lobby. */
async function openRoom(browser: Browser, options: BrowserContextOptions): Promise<Page> {
  const host = await openPlayer(browser, "Host", options);
  await host.getByRole("button", { name: /create room/i }).click();
  await expect(host).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  const roomCode = host.url().split("/rooms/")[1] ?? "";

  const guest = await openPlayer(browser, "Guest", options);
  await guest.locator("input.hd-input--code").fill(roomCode);
  await guest.getByRole("button", { name: /join room/i }).click();
  await expect(host.getByRole("heading", { name: /players \(2\)/i })).toBeVisible();
  return host;
}

test("touch targets are 44 px and Finish stays on a phone screen", async ({ browser }) => {
  test.setTimeout(60_000);
  const host = await openRoom(browser, PHONE);

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

test("home footer links and the language picker are 44 px", async ({ browser }) => {
  const page = await (await browser.newContext(PHONE)).newPage();
  await page.goto("/");
  for (const link of await page.locator(".home-footer__link").all()) await expectTarget(link);
  await page.getByRole("button", { name: /^settings$/i }).click();
  await expectTarget(page.getByRole("button", { name: /^language$/i }));
});

test("Finish stays in a short laptop window", async ({ browser }) => {
  test.setTimeout(60_000);
  const host = await openRoom(browser, LAPTOP);
  await host.getByRole("button", { name: /start game/i }).click();
  // The button is slightly rotated, so a sub-pixel corner can fall outside the sidebar's clip.
  await expect(host.getByRole("button", { name: /^finish$/i })).toBeInViewport({ ratio: 0.99 });
});
