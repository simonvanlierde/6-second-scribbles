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

  webServer: {
    command: "just e2e-dev",
    url: process.env.CI ? "http://127.0.0.1:4173" : "http://localhost:3001",
    reuseExistingServer: !process.env.CI,
    timeout: 180 * 1000,
  },
});
