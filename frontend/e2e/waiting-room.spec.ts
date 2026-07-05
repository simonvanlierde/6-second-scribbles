import { expect, test } from "@playwright/test";

type E2EPage = Parameters<Parameters<typeof test>[1]>[0]["page"];

// The name now lives in the Settings panel (opened from the gear), not on Home.
async function setPlayerName(page: E2EPage, name: string) {
  await page.getByRole("button", { name: /^settings$/i }).click();
  const nameInput = page.getByPlaceholder(/pick a name/i);
  await nameInput.fill(name);
  await nameInput.press("Escape");
  await expect(nameInput).toBeHidden();
}

async function createRoom(page: E2EPage, playerName = "Test Player") {
  await page.goto("/");
  await setPlayerName(page, playerName);
  await page.getByRole("button", { name: /create room/i }).click();
  await expect(page).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);

  const roomCode = page.url().split("/rooms/")[1];
  if (!roomCode) throw new Error("Expected room code in URL");
  return roomCode;
}

test.describe("Waiting room", () => {
  test("create room lands on the lobby with the generated room code", async ({ page }) => {
    const roomCode = await createRoom(page);

    await expect(page.getByRole("button", { name: /leave room/i })).toBeVisible();
    await expect(page.locator('button[title="Click to copy room code"] span')).toHaveText(roomCode);
    await expect(page.getByRole("heading", { name: /players/i })).toBeVisible();
  });

  test("joining a room uppercases typed room codes before navigation", async ({ page }) => {
    const hostPage = await page.context().newPage();
    const roomCode = await createRoom(hostPage);

    await page.goto("/");
    await setPlayerName(page, "Joiner");
    await page.locator("input.hd-input--code").fill(roomCode.toLowerCase());
    await page.getByRole("button", { name: /join room/i }).click();

    await expect(page).toHaveURL(new RegExp(`/rooms/${roomCode}$`));
    await hostPage.close();
  });

  test("back dialog can be cancelled without leaving the room", async ({ page }) => {
    const roomCode = await createRoom(page);

    await page.getByRole("button", { name: /leave room/i }).click();
    await expect(page.getByText(/leave room\?/i)).toBeVisible();
    await page.getByRole("button", { name: /^cancel$/i }).click();

    await expect(page).toHaveURL(new RegExp(`/rooms/${roomCode}$`));
    await expect(page.getByRole("button", { name: /leave room/i })).toBeVisible();
  });

  test("confirming leave returns to the lobby", async ({ page }) => {
    await createRoom(page);

    await page.getByRole("button", { name: /leave room/i }).click();
    await page.getByRole("button", { name: /^leave$/i }).click();

    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
  });

  test("local drawpad toggle hides and shows the shared canvas", async ({ page }) => {
    await createRoom(page);

    const canvas = page.locator("canvas.mini-canvas");
    await expect(canvas).toBeVisible();

    await page.getByRole("button", { name: /hide my pad/i }).click();
    await expect(canvas).toBeHidden();

    await page.getByRole("button", { name: /show my pad/i }).click();
    await expect(canvas).toBeVisible();
  });
});
