import { type Browser, expect, type Page, test } from "@playwright/test";

// The drawing screen on portrait phones: the smallest supported screen and a common one.
const SCREENS = [
  { width: 320, height: 568 },
  { width: 390, height: 844 },
] as const;
const MIN_CANVAS = 260;

// Ten long compound words, as German and Finnish produce them.
// cspell:disable
const LONG_PROMPTS = [
  "Donaudampfschifffahrtsgesellschaft",
  "Rindfleischetikettierungsüberwachung",
  "Kolmivaihekilowattituntimittari",
  "Epäjärjestelmällisyys",
  "Hochgeschwindigkeitszugstrecke",
  "Lentokonesuihkuturbiinimoottorimekaanikko",
  "Handschuhschneeballwerfer",
  "Atomivoimalaitosturvallisuus",
  "Zahnbürstenaufbewahrungsbecher",
  "Ensimmäisenluokanlentokapteeni",
];
// cspell:enable

type Theme = "light" | "dark";

/** Opens a room with two players and starts the game; returns the host in the drawing phase. */
async function startDrawing(
  browser: Browser,
  screen: { width: number; height: number },
  { theme = "light", longPrompts = false }: { theme?: Theme; longPrompts?: boolean } = {},
): Promise<Page> {
  const options = { viewport: screen, hasTouch: true, isMobile: true };
  const open = async (name: string) => {
    const page = await (await browser.newContext(options)).newPage();
    await page.addInitScript((value) => localStorage.setItem("ds:theme", value), theme);
    if (longPrompts) {
      // Swap every prompt list the server sends for ten long ones.
      await page.routeWebSocket(/\/ws\//, (ws) => {
        const server = ws.connectToServer();
        ws.onMessage((message) => {
          server.send(message);
        });
        server.onMessage((message) => {
          ws.send(
            typeof message === "string"
              ? message.replace(/"items":\[[^\]]*\]/g, `"items":${JSON.stringify(LONG_PROMPTS)}`)
              : message,
          );
        });
      });
    }
    await page.goto("/");
    await page.getByRole("button", { name: /^settings$/i }).click();
    const nameInput = page.getByPlaceholder(/pick a name/i);
    await nameInput.fill(name);
    await nameInput.press("Escape");
    await expect(nameInput).toBeHidden();
    return page;
  };

  const host = await open("Host");
  await host.getByRole("button", { name: /create room/i }).click();
  await expect(host).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  const roomCode = host.url().split("/rooms/")[1] ?? "";
  const guest = await open("Guest");
  await guest.locator("input.hd-input--code").fill(roomCode);
  await guest.getByRole("button", { name: /join room/i }).click();
  await expect(host.getByRole("heading", { name: /players \(2\)/i })).toBeVisible();
  await host.getByRole("button", { name: /start game/i }).click();
  await expect(host.locator(".category-card__item").first()).toBeVisible();
  return host;
}

async function canvasHeight(page: Page): Promise<number> {
  return Math.round(
    (await page.locator(".canvas-stage canvas").evaluate((el) => el.getBoundingClientRect().height)) ?? 0,
  );
}

async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() =>
    Math.max(
      document.documentElement.scrollWidth - window.innerWidth,
      ...[...document.querySelectorAll("main, main *")].map(
        (el) => el.getBoundingClientRect().right - window.innerWidth,
      ),
    ),
  );
  expect(overflow).toBeLessThanOrEqual(1);
}

/** Scrolls an element into view inside whatever scrolls, and checks that it ends up on screen. */
async function expectReachable(locator: ReturnType<Page["locator"]>) {
  await locator.scrollIntoViewIfNeeded();
  await expect(locator).toBeInViewport({ ratio: 0.99 });
}

async function expectScreenFits(page: Page, screen: { width: number; height: number }) {
  expect(await canvasHeight(page)).toBeGreaterThanOrEqual(MIN_CANVAS);
  await expectNoHorizontalScroll(page);
  const finish = page.getByRole("button", { name: /^finish$/i });
  await expect(finish).toBeInViewport({ ratio: 1 });

  const items = page.locator(".category-card__item");
  expect(await items.count()).toBe(10);
  for (const item of await items.all()) await expectReachable(item);

  for (const control of await page.locator(".toolbar .swatch, .toolbar .brush, .toolbar button.hd-icon-btn").all()) {
    await expectReachable(control);
  }
  // The persistent Finish button covers nothing it should not: it stays on screen after all that scrolling.
  await expect(finish).toBeInViewport({ ratio: 1 });
  expect(page.viewportSize()).toEqual(screen);
}

/** Draws one stroke with real touch events (Chromium only), as a finger would. */
async function touchStroke(page: Page) {
  const box = await page.locator(".canvas-stage canvas").boundingBox();
  if (!box) throw new Error("Expected a canvas");
  const session = await page.context().newCDPSession(page);
  const point = (fx: number, fy: number) => [{ x: box.x + box.width * fx, y: box.y + box.height * fy }];
  await session.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: point(0.2, 0.2) });
  for (let step = 1; step <= 10; step++) {
    await session.send("Input.dispatchTouchEvent", {
      type: "touchMove",
      touchPoints: point(0.2 + step * 0.06, 0.2 + step * 0.05),
    });
  }
  await session.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
}

function inkedPixels(page: Page): Promise<number> {
  return page.locator(".canvas-stage canvas").evaluate((el) => {
    const canvas = el as HTMLCanvasElement;
    const data = canvas.getContext("2d")?.getImageData(0, 0, canvas.width, canvas.height).data ?? [];
    let count = 0;
    for (let index = 3; index < data.length; index += 4) if ((data[index] ?? 0) > 0) count++;
    return count;
  });
}

function scrollPositions(page: Page): Promise<number[]> {
  return page.evaluate(() => [window.scrollY, document.querySelector(".drawing-phase__body")?.scrollTop ?? 0]);
}

for (const screen of SCREENS) {
  test(`${screen.width}x${screen.height}: canvas, prompts and toolbar fit`, async ({ browser }) => {
    test.setTimeout(60_000);
    const host = await startDrawing(browser, screen);
    await expectScreenFits(host, screen);
    expect(await canvasHeight(host)).toBeGreaterThanOrEqual(MIN_CANVAS);
  });
}

test("a touch stroke draws without scrolling the page", async ({ browser }) => {
  test.setTimeout(60_000);
  const host = await startDrawing(browser, SCREENS[0]);
  await host.locator(".canvas-stage").scrollIntoViewIfNeeded();
  const before = await scrollPositions(host);
  await touchStroke(host);
  expect(await inkedPixels(host)).toBeGreaterThan(0);
  expect(await scrollPositions(host)).toEqual(before);
});

test("resizing keeps the strokes", async ({ browser }) => {
  test.setTimeout(60_000);
  const host = await startDrawing(browser, SCREENS[1]);
  await touchStroke(host);
  expect(await inkedPixels(host)).toBeGreaterThan(0);
  // Landscape and back, as a rotated phone does.
  await host.setViewportSize({ width: SCREENS[1].height, height: SCREENS[1].width });
  await host.setViewportSize(SCREENS[1]);
  await expect.poll(() => inkedPixels(host)).toBeGreaterThan(0);
});

for (const theme of ["light", "dark"] as const) {
  test(`ten long prompts fit at 320x568 in the ${theme} theme`, async ({ browser }) => {
    test.setTimeout(60_000);
    const host = await startDrawing(browser, SCREENS[0], { theme, longPrompts: true });
    await expect(host.locator(".category-card__text").first()).toHaveText(LONG_PROMPTS[0] ?? "");
    await expectScreenFits(host, SCREENS[0]);
    // A prompt can be ticked off, and the tick shows.
    await host.locator(".category-card__item").first().click();
    await expect(host.locator(".category-card__item--done")).toHaveCount(1);
  });
}
