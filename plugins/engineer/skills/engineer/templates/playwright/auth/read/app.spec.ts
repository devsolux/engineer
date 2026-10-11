import { test, expect } from "../../fixtures";

/**
 * Runs only in project "auth-read-desktop" with storageState from auth.setup.ts.
 * Replace paths with your app's critical path.
 */
test.describe("authenticated app", () => {
  test("dashboard shell", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByRole("navigation").or(page.getByRole("main"))).toBeVisible();
  });

  test("settings reachable", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: /settings|account|profile/i })).toBeVisible();
  });

  test("keyboard focus reaches the main action", async ({ page }) => {
    await page.goto("/dashboard");
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toBeVisible();
  });
});
