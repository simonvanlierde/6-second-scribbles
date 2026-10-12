import { type Browser, expect, type Page, test } from "@playwright/test";

// The backend drops any WebSocket frame over 64 KiB (ws_max_message_bytes), so
// a finished drawing has to fit in one frame with room to spare.
const MAX_FRAME_BYTES = 64 * 1024;

// A HiDPI laptop screen: the canvas backing store is CSS size x 2.
const HIGH_DENSITY = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 };

async function openPlayer(browser: Browser, name: string): Promise<{ page: Page; sentDrawings: number[] }> {
  const context = await browser.newContext(HIGH_DENSITY);
  const page = await context.newPage();
  const sentDrawings: number[] = [];
  page.on("websocket", (ws) => {
    ws.on("framesent", ({ payload }) => {
      const text = typeof payload === "string" ? payload : payload.toString("utf8");
      if (text.includes('"type":"draw_stroke"')) sentDrawings.push(Buffer.byteLength(text, "utf8"));
    });
  });
  await page.goto("/");
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
  return { page, sentDrawings };
}

// A dense scribble: many overlapping strokes in several colours, like a player
// filling the whole canvas in the time they have.
async function scribble(page: Page) {
  const canvas = page.locator(".drawing-phase canvas");
  await expect(canvas).toBeVisible();
  const box = await canvas.boundingBox();
  if (!box) throw new Error("Expected the drawing canvas to have a size");

  const swatches = page.getByRole("group", { name: /color/i }).first().getByRole("button");
  const swatchCount = await swatches.count();
  let seed = 7;
  const rand = () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };

  for (let stroke = 0; stroke < 40; stroke++) {
    if (swatchCount > 0) await swatches.nth(stroke % swatchCount).click();
    let x = box.x + box.width * (0.05 + rand() * 0.9);
    let y = box.y + box.height * (0.05 + rand() * 0.9);
    await page.mouse.move(x, y);
    await page.mouse.down();
    for (let point = 0; point < 25; point++) {
      x = Math.min(box.x + box.width - 2, Math.max(box.x + 2, x + (rand() - 0.5) * 120));
      y = Math.min(box.y + box.height - 2, Math.max(box.y + 2, y + (rand() - 0.5) * 120));
      await page.mouse.move(x, y, { steps: 2 });
    }
    await page.mouse.up();
  }
}

test("a dense HiDPI drawing reaches the guesser", async ({ browser }) => {
  test.setTimeout(90_000);
  const host = await openPlayer(browser, "Host");
  await host.page.getByRole("button", { name: /create room/i }).click();
  await expect(host.page).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  const roomCode = host.page.url().split("/rooms/")[1] ?? "";

  const guest = await openPlayer(browser, "Guest");
  await guest.page.locator("input.hd-input--code").fill(roomCode);
  await guest.page.getByRole("button", { name: /join room/i }).click();
  await expect(host.page.getByRole("heading", { name: /players \(2\)/i })).toBeVisible();

  await host.page.getByRole("button", { name: /start game/i }).click();

  // Both draw at once: the round timer keeps running for everyone.
  await Promise.all(
    [host, guest].map(async ({ page }) => {
      await scribble(page);
      await page
        .getByRole("button", { name: /^finish$/i })
        .first()
        .click();
    }),
  );

  for (const player of [host, guest]) {
    await expect.poll(() => player.sentDrawings.length).toBe(1);
    const [bytes = 0] = player.sentDrawings;
    test.info().annotations.push({ type: "drawing frame bytes", description: String(bytes) });
    expect(bytes).toBeLessThan(MAX_FRAME_BYTES);
    await expect(player.page.getByRole("img", { name: /player drawing/i })).toBeVisible({ timeout: 15_000 });
  }
});
