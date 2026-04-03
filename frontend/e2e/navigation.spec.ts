import { expect, test } from "@playwright/test";

test.describe("Routing", () => {
  test("/ renders the Lobby view", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
    await expect(page.locator("#player-name")).toBeVisible();
  });

  test("unknown route redirects to the Lobby", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
  });
});
