import { expect, test } from "@playwright/test";

// The name now lives in the Settings panel (opened from the gear), not on Home.
async function setPlayerName(page: Parameters<Parameters<typeof test>[1]>[0]["page"], name: string) {
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
}

test.describe("Home page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("renders key UI elements", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /create room/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /join room/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /quick-play/i })).toBeVisible();
    await expect(page.locator("input.hd-input--code")).toBeVisible();
  });

  test("create room button works when a name is set", async ({ page }) => {
    await setPlayerName(page, "Test Player");
    await page.getByRole("button", { name: /create room/i }).click();
    // Should navigate away from Home into a room
    await expect(page).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  });

  test("creating without a name opens the name prompt, then resumes", async ({ page }) => {
    await page.getByRole("button", { name: /create room/i }).click();
    // Settings opens focused on the name field with a prompt explaining why.
    const nameInput = page.getByPlaceholder(/pick a name/i);
    await expect(nameInput).toBeVisible();
    // Typing a name and confirming resumes the Create Room action.
    await nameInput.fill("Late Namer");
    await nameInput.press("Enter");
    await expect(page).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);
  });

  test("shows an error when joining without a room code", async ({ page }) => {
    await setPlayerName(page, "Test Player");
    await page.getByRole("button", { name: /join room/i }).click();
    await expect(page.getByRole("alert")).toContainText(/room code/i);
  });

  test("room code input accepts a 6-character code", async ({ page }) => {
    const input = page.locator("input.hd-input--code");
    await input.fill("ABCDEF");
    await expect(input).toHaveValue(/ABCDEF/i);
  });

  test("player name persists after page reload", async ({ page }) => {
    await setPlayerName(page, "Persistent Player");
    await page.reload();
    await page.getByRole("button", { name: /^settings$/i }).click();
    await expect(page.getByPlaceholder(/pick a name/i)).toHaveValue("Persistent Player");
  });
});
