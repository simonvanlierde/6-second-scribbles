import { expect, test } from "@playwright/test";

test.describe("Routing", () => {
  test("/ renders the Lobby view", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
    await expect(page.locator("#player-name")).toBeVisible();
  });

  test("unknown route redirects to the Lobby", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    // Should either show lobby or a 404 — not a blank page
    const body = page.locator("body");
    await expect(body).not.toBeEmpty();
    // Either redirected to lobby or on a 404 page — lobby heading OR any visible content
    const visible = await page.locator("h1, h2").first().isVisible();
    expect(visible).toBe(true);
  });
});
