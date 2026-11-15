import { type Browser, expect, type Page, test } from "@playwright/test";

// 390x500 approximates an iPhone with its software keyboard open; 320x568 is the narrowest
// phone the layout supports. A real keyboard is not emulated.
const VIEWPORTS = [
  { width: 390, height: 500 },
  { width: 320, height: 568 },
];
const GUESS_COUNT = 10;
// Below this the drawing is too small to guess from.
const MIN_DRAWING_HEIGHT = 150;

async function openPlayer(browser: Browser, name: string, options: object): Promise<Page> {
  const page = await (await browser.newContext(options)).newPage();
  await page.goto("/");
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
  return page;
}

/** Plays a two-player game up to the guessing screen and returns the guest's page. */
async function openGuessing(
  browser: Browser,
  scheme: "light" | "dark",
  viewport: { width: number; height: number },
): Promise<Page> {
  const host = await openPlayer(browser, "Host", { colorScheme: scheme });
  await host.getByRole("button", { name: /create room/i }).click();
  await expect(host).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  const roomCode = host.url().split("/rooms/")[1] ?? "";

  const guest = await openPlayer(browser, "Guest", {
    colorScheme: scheme,
    viewport: { width: 1280, height: 720 },
    hasTouch: true,
    isMobile: true,
  });
  await guest.locator("input.hd-input--code").fill(roomCode);
  await guest.getByRole("button", { name: /join room/i }).click();
  await expect(host.getByRole("heading", { name: /players \(2\)/i })).toBeVisible();
  await host.getByRole("button", { name: /start game/i }).click();

  for (const page of [host, guest]) {
    // An empty drawing cannot be finished. Draw at desktop size: the phone drawing layout is a separate fix.
    const canvas = page.locator(".drawing-phase canvas");
    await expect(canvas).toBeVisible({ timeout: 15_000 });
    const box = await canvas.boundingBox();
    if (!box) throw new Error("Expected the drawing canvas to have a size");
    await page.mouse.move(box.x + box.width * 0.2, box.y + box.height * 0.3);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.7, { steps: 8 });
    await page.mouse.up();
    await page
      .getByRole("button", { name: /^finish$/i })
      .first()
      .click();
  }
  await guest.setViewportSize(viewport);
  await expect(guest.getByRole("button", { name: /submit guesses/i })).toBeVisible({ timeout: 20_000 });
  return guest;
}

async function noHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const root = document.documentElement;
    return Math.max(root.scrollWidth, document.body.scrollWidth) - root.clientWidth;
  });
  expect(overflow).toBeLessThanOrEqual(0);
}

for (const scheme of ["light", "dark"] as const) {
  for (const viewport of VIEWPORTS) {
    test(`guessing fits a short phone screen ${viewport.width}x${viewport.height} — ${scheme}`, async ({ browser }) => {
      test.setTimeout(120_000);
      const guest = await openGuessing(browser, scheme, viewport);
      const submit = guest.getByRole("button", { name: /submit guesses/i });
      const drawing = guest.getByRole("img", { name: /player drawing/i });

      await expect(drawing).toBeVisible();
      const imageBox = await drawing.boundingBox();
      const submitBox = await submit.boundingBox();
      const panelBox = await guest.locator(".guess-panel").boundingBox();
      const measured = JSON.stringify({ imageBox, panelBox, submitBox });
      test.info().annotations.push({ type: "measured", description: measured });
      console.log(`MEASURED ${viewport.width}x${viewport.height} ${scheme} ${measured}`);
      await expect(submit).toBeInViewport({ ratio: 1 });
      expect(imageBox?.height ?? 0).toBeGreaterThanOrEqual(MIN_DRAWING_HEIGHT);
      await noHorizontalOverflow(guest);

      // Enter moves to the next field, and the focused field stays on screen while ten are typed.
      await guest.getByRole("textbox", { name: /^guess 1$/i }).click();
      for (let i = 1; i <= GUESS_COUNT; i++) {
        const field = guest.getByRole("textbox", { name: new RegExp(`^guess ${i}$`, "i") });
        await expect(field).toBeFocused();
        await expect(field).toBeInViewport({ ratio: 1 });
        await guest.keyboard.type(`guess ${i}`);
        await expect(submit).toBeInViewport({ ratio: 1 });
        if (i < GUESS_COUNT) await guest.keyboard.press("Enter");
      }
      await expect(guest.getByRole("textbox", { name: /^guess 11$/i })).toHaveCount(0);

      // Each field has a visible label, so the placeholder is not the only one.
      await expect(guest.locator(".guess-row__num").first()).toBeVisible();

      // Edit a field in the middle of the list.
      const third = guest.getByRole("textbox", { name: /^guess 3$/i });
      await third.focus();
      await expect(third).toBeInViewport({ ratio: 1 });
      await third.fill("edited");
      await expect(third).toHaveValue("edited");
      await expect(submit).toBeInViewport({ ratio: 1 });
      await noHorizontalOverflow(guest);

      // The draft survives a reload (reconnect).
      await guest.reload();
      await expect(guest.getByRole("textbox", { name: /^guess 3$/i })).toHaveValue("edited", { timeout: 15_000 });
      await expect(guest.getByRole("textbox", { name: /^guess 10$/i })).toHaveValue("guess 10");
      await expect(guest.getByRole("button", { name: /submit guesses/i })).toBeInViewport({ ratio: 1 });
    });
  }
}
