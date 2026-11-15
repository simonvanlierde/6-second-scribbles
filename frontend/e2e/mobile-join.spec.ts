import { expect, type Page, test } from "@playwright/test";

// Phone widths from the roadmap: the smallest phone, and a 390 px phone with the
// software keyboard open (about 500 px of height left).
const SIZES = [
  { width: 320, height: 568 },
  { width: 390, height: 500 },
];
const MIN_TEXT_CONTRAST = 3;

// The backend is not needed: the room status call is answered here.
async function mockRoom(page: Page, status: object = { exists: true, players: 2, game_phase: "lobby" }) {
  await page.route("**/api/rooms/*/status", (route) => route.fulfill({ json: status }));
}

// The name lives in the Settings panel, and Join on Home needs one.
async function setPlayerName(page: Page, name: string) {
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
}

function luminance(rgb: number[]): number {
  const [r = 0, g = 0, b = 0] = rgb.map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: number[], b: number[]): number {
  const [hi = 0, lo = 0] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Resolves any CSS colour to rgb through a canvas pixel, so light-dark() and color-mix() work.
async function colours(page: Page, selector: string): Promise<{ fg: number[]; bg: number[]; opacity: number }> {
  return page.locator(selector).evaluate((el) => {
    const px = (css: string) => {
      const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
      if (!ctx) throw new Error("no canvas");
      ctx.canvas.width = ctx.canvas.height = 1;
      ctx.fillStyle = css;
      ctx.fillRect(0, 0, 1, 1);
      return Array.from(ctx.getImageData(0, 0, 1, 1).data).slice(0, 3);
    };
    const s = getComputedStyle(el);
    return { fg: px(s.color), bg: px(s.backgroundColor), opacity: Number(s.opacity) };
  });
}

for (const size of SIZES) {
  test.describe(`${size.width}x${size.height}`, () => {
    test.use({ viewport: size, hasTouch: true, isMobile: true });

    test("room code input is tuned for phones and its placeholder fits", async ({ page }) => {
      await page.goto("/");
      const code = page.locator("input.hd-input--code");
      await expect(code).toHaveAttribute("autocapitalize", "characters");
      await expect(code).toHaveAttribute("autocorrect", "off");
      await expect(code).toHaveAttribute("spellcheck", "false");
      await expect(code).toHaveAttribute("autocomplete", "off");
      // Measure the placeholder text in the placeholder's own font against the input's content box.
      const { need, room } = await code.evaluate((el: HTMLInputElement) => {
        const s = getComputedStyle(el, "::placeholder");
        const probe = document.createElement("span");
        probe.style.cssText = `position:absolute;visibility:hidden;white-space:nowrap;font:${s.font};letter-spacing:${s.letterSpacing};text-transform:${s.textTransform}`;
        probe.textContent = el.placeholder;
        document.body.append(probe);
        const need = probe.getBoundingClientRect().width;
        probe.remove();
        const cs = getComputedStyle(el);
        return { need, room: el.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) };
      });
      expect(need).toBeLessThanOrEqual(room);
    });

    test("join works with a lowercase code and Enter", async ({ page }) => {
      await mockRoom(page);
      await page.goto("/");
      await setPlayerName(page, "Ann");
      const code = page.locator("input.hd-input--code");
      await code.fill("abc123");
      await code.press("Enter");
      await expect(page).toHaveURL(/\/rooms\/ABC123$/);
    });

    test("an unknown room is refused on Home", async ({ page }) => {
      await mockRoom(page, { exists: false });
      await page.goto("/");
      await setPlayerName(page, "Ann");
      await page.locator("input.hd-input--code").fill("zzzzzz");
      await page.getByRole("button", { name: /join room/i }).click();
      await expect(page.getByText(/doesn't exist/i)).toBeVisible();
      await expect(page).toHaveURL(/\/$/);
    });

    test("name field focused: Join stays visible, no overflow, disabled reason is shown", async ({ page }) => {
      await mockRoom(page);
      await page.goto("/rooms/abc123");
      const join = page.getByRole("button", { name: /join room/i });
      await expect(join).toBeVisible();
      await page.getByLabel(/enter your name/i).focus();
      await expect(join).toBeDisabled();
      await expect(join).toBeInViewport({ ratio: 1 });
      expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);

      // The reason is visible text tied to the button, not colour alone.
      const hint = page.locator("#join-hint");
      await expect(hint).toBeVisible();
      await expect(hint).toHaveText(/name to join/i);
      await expect(join).toHaveAttribute("aria-describedby", "join-hint");

      const disabled = await colours(page, ".access-actions .hd-btn--primary");
      expect(contrast(disabled.fg, disabled.bg)).toBeGreaterThanOrEqual(MIN_TEXT_CONTRAST);
      expect(disabled.opacity).toBe(1);

      await page.getByLabel(/enter your name/i).fill("Ann");
      await expect(join).toBeEnabled();
      await expect(hint).toBeHidden();
      await expect(join).toBeInViewport({ ratio: 1 });
    });

    test("an invalid code shows no join form", async ({ page }) => {
      await page.goto("/rooms/bad");
      await expect(page.getByRole("heading", { name: /invalid room code/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /join room/i })).toHaveCount(0);
    });
  });
}
