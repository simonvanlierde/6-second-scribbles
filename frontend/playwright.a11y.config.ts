import process from "node:process";
import { defineConfig, devices } from "@playwright/test";

// Accessibility (axe) checks only. These scan frontend-only screens (Home,
// Settings, the /__ds component library) so they need just the dev server — no
// backend, no Docker. Kept separate from playwright.config.ts, whose webServer
// stands up the full stack for the backend-dependent flows.
export default defineConfig({
  testDir: "./e2e",
  testMatch: "a11y.spec.ts",
  timeout: 30 * 1000,
  expect: { timeout: 5000 },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "list" : "html",
  use: {
    baseURL: "http://localhost:3001",
    trace: "on-first-retry",
    headless: true,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "pnpm run dev",
    url: "http://localhost:3001",
    reuseExistingServer: !process.env.CI,
    timeout: 60 * 1000,
  },
});
