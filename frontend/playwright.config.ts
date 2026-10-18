import process from "node:process";
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30 * 1000,
  expect: {
    timeout: 5000,
  },
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    actionTimeout: 2000,
    baseURL: process.env.CI ? "http://127.0.0.1:4173" : "http://localhost:3001",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    headless: true,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
      grep: /@cross-browser/,
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
      grep: /@cross-browser/,
    },
  ],

  // CI provides Postgres and Redis as service containers and runs migrations
  // first, so it only needs the backend and the built bundle. `vite preview`
  // reuses the dev server's /api and /ws proxy, keeping the page same-origin.
  webServer: process.env.CI
    ? [
        {
          command: "cd ../backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000",
          url: "http://127.0.0.1:8000/api/health",
          timeout: 60 * 1000,
          // The suite creates many rooms from one IP, and retries add more, so the
          // defaults (10 rooms/min, 5 open rooms per network) would answer 429.
          env: { ROOM_CREATION_RATE_LIMIT: "1000", MAX_ROOMS_PER_CLIENT: "1000" },
        },
        {
          command: "pnpm run build && pnpm exec vite preview --host 127.0.0.1 --port 4173 --strictPort",
          url: "http://127.0.0.1:4173",
          timeout: 120 * 1000,
        },
      ]
    : {
        command: "just e2e-dev",
        url: "http://localhost:3001",
        reuseExistingServer: true,
        timeout: 180 * 1000,
      },
});
