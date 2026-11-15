import { expect, test } from "@playwright/test";

// Frontend-only: the /__ds page renders the real HdDialog and HdToast in a
// browser, where top-layer stacking and hit testing are real.
test.describe("overlays", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/__ds");
    await page.getByRole("button", { name: "Open dialog" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("a click on the dialog's own padding keeps it open", async ({ page }) => {
    await page.getByRole("dialog").click({ position: { x: 6, y: 6 } });
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("a click on the backdrop closes the dialog", async ({ page }) => {
    await page.mouse.click(3, 3);
    await expect(page.getByRole("dialog")).toBeHidden();
  });

  test("a toast shows above the modal backdrop", async ({ page }) => {
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toBeHidden();
    await page.getByRole("button", { name: "Show toast in 0.5 s" }).click();
    await page.getByRole("button", { name: "Open dialog" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    // The toast arrives while the modal is already open.
    const toast = page.locator(".hd-toast", { hasText: "Hello from a toast" }).first();
    await expect(toast).toBeVisible();
    const box = await toast.boundingBox();
    if (!box) throw new Error("toast has no box");
    // The modal makes the page inert, so hit testing cannot tell; compare pixels.
    // Behind the backdrop the toast's yellow is dimmed; its red channel stays bright in front.
    const shot = await page.screenshot({ clip: { x: box.x + 7, y: box.y + box.height / 2, width: 2, height: 2 } });
    const red = await page.evaluate(async (b64) => {
      const bitmap = await createImageBitmap(await (await fetch(`data:image/png;base64,${b64}`)).blob());
      const ctx = new OffscreenCanvas(bitmap.width, bitmap.height).getContext("2d");
      ctx?.drawImage(bitmap, 0, 0);
      return ctx?.getImageData(0, 0, 1, 1).data[0] ?? 0;
    }, shot.toString("base64"));
    expect(red).toBeGreaterThan(200);
  });
});
