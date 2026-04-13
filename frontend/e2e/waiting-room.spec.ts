import { expect, test } from "@playwright/test";

async function createRoom(page: Parameters<typeof test>[0]["page"], playerName = "Test Player") {
  await page.goto("/");
  await page.locator("#player-name").fill(playerName);
  await page.getByRole("button", { name: /create room/i }).click();
  await expect(page).toHaveURL(/\/rooms\/[A-Z0-9]{6}$/);

  const roomCode = page.url().split("/rooms/")[1];
  if (!roomCode) throw new Error("Expected room code in URL");
  return roomCode;
}

test.describe("Waiting room", () => {
  test("create room lands on a waiting room with the generated room code", async ({ page }) => {
    const roomCode = await createRoom(page);

    await expect(page.getByRole("heading", { name: new RegExp(`room: ${roomCode}`, "i") })).toBeVisible();
    await expect(page.locator(".room-code-display")).toHaveText(roomCode);
    await expect(page.getByText(/share this room code with friends/i)).toBeVisible();
  });

  test("joining a room uppercases typed room codes before navigation", async ({ page }) => {
    await page.goto("/");
    await page.locator("#player-name").fill("Joiner");
    const inputs = page.locator("input.code-input");
    await inputs.nth(0).fill("a");
    await inputs.nth(1).fill("b");
    await inputs.nth(2).fill("1");
    await inputs.nth(3).fill("2");
    await inputs.nth(4).fill("c");
    await page.getByRole("button", { name: /join room/i }).click();

    await expect(page).toHaveURL(/\/rooms\/AB12C$/);
    await expect(page.getByRole("heading", { name: /room: ab12c/i })).toBeVisible();
  });

  test("back dialog can be cancelled without leaving the room", async ({ page }) => {
    const roomCode = await createRoom(page);

    await page.getByRole("button", { name: /back/i }).click();
    await expect(page.getByText(/leave room\?/i)).toBeVisible();
    await page.getByRole("button", { name: /^cancel$/i }).click();

    await expect(page).toHaveURL(new RegExp(`/rooms/${roomCode}$`));
    await expect(page.getByRole("heading", { name: new RegExp(`room: ${roomCode}`, "i") })).toBeVisible();
  });

  test("confirming leave returns to the lobby", async ({ page }) => {
    await createRoom(page);

    await page.getByRole("button", { name: /back/i }).click();
    await page.getByRole("button", { name: /^leave$/i }).click();

    await expect(page).toHaveURL("/");
    await expect(page.getByRole("heading", { name: /six second scribbles/i })).toBeVisible();
  });

  test("local drawpad toggle hides and shows the shared canvas", async ({ page }) => {
    await createRoom(page);

    const canvas = page.locator("canvas.mini-canvas");
    await expect(canvas).toBeVisible();

    await page.getByRole("button", { name: /hide pad/i }).click();
    await expect(canvas).toBeHidden();

    await page.getByRole("button", { name: /show pad/i }).click();
    await expect(canvas).toBeVisible();
  });
});
