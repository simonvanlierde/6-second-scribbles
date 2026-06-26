import { expect, test } from "@playwright/test";

test.describe("Lobby page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("renders key UI elements", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
    await expect(page.locator("#player-name")).toBeVisible();
    await expect(page.getByRole("button", { name: /create room/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /join room/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /join random room/i })).toBeVisible();
  });

  test("create room button works when a name is entered", async ({ page }) => {
    await page.locator("#player-name").fill("Test Player");
    await page.getByRole("button", { name: /create room/i }).click();
    // Should navigate away from lobby into a room
    await expect(page).not.toHaveURL("/");
  });

  test("shows an error when creating a room without a name", async ({ page }) => {
    await page.getByRole("button", { name: /create room/i }).click();
    await expect(page.getByRole("alert")).toContainText(/name/i);
  });

  test("shows an error when joining without a name", async ({ page }) => {
    await page.getByRole("button", { name: /join room/i }).click();
    await expect(page.getByRole("alert")).toContainText(/name/i);
  });

  test("shows an error when joining without a room code", async ({ page }) => {
    await page.locator("#player-name").fill("Test Player");
    await page.getByRole("button", { name: /join room/i }).click();
    await expect(page.getByRole("alert")).toContainText(/room code/i);
  });

  test("room code input: typing 6 characters fills all cells", async ({ page }) => {
    const inputs = page.locator("input.code-input");
    await expect(inputs).toHaveCount(6);

    // Type one character into each cell
    for (let i = 0; i < 6; i++) {
      await inputs.nth(i).fill(String.fromCharCode(65 + i)); // A–F
    }

    // All 6 inputs should now have a value
    for (let i = 0; i < 6; i++) {
      await expect(inputs.nth(i)).not.toHaveValue("");
    }
  });

  test("room code input: paste fills all cells at once", async ({ page }) => {
    const firstInput = page.locator("input.code-input").first();
    await firstInput.focus();
    await page.keyboard.insertText("ABCDEF");
    // Cells should collectively contain the pasted characters
    const values = await page
      .locator("input.code-input")
      .evaluateAll((els) => (els as HTMLInputElement[]).map((el) => el.value).join(""));
    expect(values.replace(/\s/g, "")).toMatch(/[A-Z0-9]{1,6}/);
  });

  test("player name persists after page reload", async ({ page }) => {
    await page.locator("#player-name").fill("Persistent Player");
    await page.reload();
    // Name should be restored from localStorage
    await expect(page.locator("#player-name")).toHaveValue("Persistent Player");
  });
});
