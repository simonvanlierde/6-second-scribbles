import { expect, test } from "@playwright/test";

test.describe("Routing", () => {
  test("/ renders the Home view", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /create room/i })).toBeVisible();
  });

  test("unknown route redirects to Home", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
  });
});
