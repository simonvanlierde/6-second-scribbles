// Renders public/og.png. Step 1 drives the running app (served by Vite): the drawing screen is
// put in its last six seconds, a scribble is drawn on the real canvas with the mouse, and the
// canvas and timer are captured to docs/og-paper.png and docs/og-timer.png. Step 2 screenshots
// docs/og-card.html. Run `pnpm og-card` (Playwright Chromium needed).
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";
import { createServer } from "vite";

const root = fileURLToPath(new URL("../../", import.meta.url));
const PORT = 4182;
const NOW = new Date("2026-07-16T12:00:00Z");

// One loose cat, drawn fast: [pen colour, brush size, points as fractions of the canvas].
const COLOR_NAMES = { "#2d2d2d": "Black", "#ff4d4d": "Red", "#2d5da1": "Blue", "#2e9e5b": "Green", "#ff8c42": "Orange" };
const SIZE_NAMES = { 6: "Medium brush", 10: "Large brush" };
const wobble = (n) => Math.sin(n * 12.9898) * 0.5 + Math.sin(n * 4.1414) * 0.5;
function loop(cx, cy, rx, ry, turns = 1.04, start = -1.2, jitter = 0.012) {
  const pts = [];
  const steps = 56;
  for (let i = 0; i <= steps * turns; i++) {
    const a = start + (i / steps) * Math.PI * 2;
    const k = 1 + jitter * 6 * wobble(i * 0.9 + cx * 7);
    pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]);
  }
  return pts;
}
const line = (...p) => p;
const STROKES = [
  ["#2d2d2d", 6, loop(0.5, 0.56, 0.3, 0.3, 1.04, -1.2, 0.006)], // head
  ["#2d2d2d", 10, line([0.24, 0.4], [0.2, 0.12], [0.2, 0.1], [0.36, 0.26])], // left ear
  ["#2d2d2d", 10, line([0.64, 0.26], [0.8, 0.1], [0.8, 0.12], [0.76, 0.4])], // right ear
  ["#2e9e5b", 10, loop(0.38, 0.5, 0.055, 0.075, 1.1)], // left eye
  ["#2e9e5b", 10, loop(0.62, 0.5, 0.055, 0.075, 1.1)], // right eye
  ["#2d2d2d", 10, loop(0.38, 0.51, 0.015, 0.03, 1)], // pupils
  ["#2d2d2d", 10, loop(0.62, 0.51, 0.015, 0.03, 1)],
  ["#ff4d4d", 10, line([0.46, 0.62], [0.54, 0.62], [0.5, 0.67], [0.46, 0.62])], // nose
  ["#2d2d2d", 6, line([0.5, 0.67], [0.5, 0.72], [0.44, 0.76], [0.4, 0.73])], // mouth
  ["#2d2d2d", 6, line([0.5, 0.72], [0.56, 0.76], [0.6, 0.73])],
  ["#2d5da1", 6, line([0.3, 0.64], [0.12, 0.6])], // whiskers
  ["#2d5da1", 6, line([0.31, 0.69], [0.12, 0.73])],
  ["#2d5da1", 6, line([0.7, 0.64], [0.88, 0.6])],
  ["#2d5da1", 6, line([0.69, 0.69], [0.88, 0.73])],
  ["#ff8c42", 10, line([0.44, 0.27], [0.45, 0.35])], // forehead stripes
  ["#ff8c42", 10, line([0.5, 0.26], [0.5, 0.36])],
  ["#ff8c42", 10, line([0.56, 0.27], [0.55, 0.35])],
];

const server = await createServer({ root: `${root}frontend`, server: { port: PORT, strictPort: true }, logLevel: "error" });
await server.listen();
const browser = await chromium.launch();
try {
  const context = await browser.newContext({ viewport: { width: 1100, height: 900 }, deviceScaleFactor: 3 });
  const page = await context.newPage();
  await page.clock.setFixedTime(NOW);
  await page.route("**/api/**", (route) => route.abort());
  await page.routeWebSocket(/.*/, () => {}); // the app waits for a server that never answers
  await page.goto(`http://localhost:${PORT}/rooms/ABC234`);
  // Put the store in the drawing phase with six seconds left, as a server snapshot would.
  await page.evaluate(
    async ([now]) => {
      const { useGameStore } = await import("/src/stores/game.svelte.ts");
      const store = useGameStore();
      store.setLocalPlayer("p1", "Mo");
      store.setRoomCode("ABC234");
      store.applyRoomState({
        gamePhase: "drawing",
        players: [{ id: "p1", name: "Mo", score: 0, connected: true }],
        hostId: "p1",
        currentRound: 1,
        maxRounds: 5,
        drawingTimeLimit: 60,
        guessingTimeLimit: 60,
        roundStartTime: now - 54_000,
        card: { category: "Animals", items: ["cat", "owl", "fish", "frog", "duck", "bee"] },
      });
    },
    [NOW.getTime()],
  );
  const canvas = page.locator(".drawing-phase canvas");
  await canvas.waitFor();
  const box = await canvas.boundingBox();
  const toolbar = page.locator(".toolbar");
  for (const [color, size, points] of STROKES) {
    await toolbar.getByRole("button", { name: COLOR_NAMES[color] }).click();
    await toolbar.getByRole("button", { name: SIZE_NAMES[size] }).click();
    const [first, ...rest] = points.map(([x, y]) => [box.x + x * box.width, box.y + y * box.height]);
    await page.mouse.move(...first);
    await page.mouse.down();
    for (const p of rest) await page.mouse.move(...p, { steps: 3 });
    await page.mouse.up();
  }
  // Only the timer and the paper: no page ground, no header, and no heartbeat.
  await page.addStyleTag({
    content: `body::before{display:none!important} html,body,#app,.drawing-phase,.game-header{background:none!important;border:0!important}
      .hd-timer{animation:none!important}`,
  });
  const shoot = async (selector, file, pad) => {
    const b = await page.locator(selector).first().boundingBox();
    await page.screenshot({
      path: `${root}docs/${file}`,
      omitBackground: true,
      clip: { x: b.x - pad, y: b.y - pad, width: b.width + 2 * pad, height: b.height + 2 * pad },
    });
  };
  await page.locator(".drawing-phase__sidebar, .drawing-phase__canvas-panel > .toolbar, .game-header > :not(.game-header__timer)").evaluateAll((els) => {
    for (const el of els) el.style.visibility = "hidden";
  });
  await shoot(".hd-timer", "og-timer.png", 12);
  await page.locator(".game-header__timer").evaluate((el) => {
    el.style.visibility = "hidden";
  });
  await shoot(".canvas-stage", "og-paper.png", 14);
  await context.close();

  const card = await browser.newPage({ viewport: { width: 1200, height: 630 } });
  await card.goto(`file://${root}docs/og-card.html`);
  await card.evaluate(() => document.fonts.ready);
  await card.screenshot({ path: `${root}frontend/public/og.png` });
} finally {
  await browser.close();
  await server.close();
}
