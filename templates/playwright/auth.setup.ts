import { test as setup, expect } from "@playwright/test";
import path from "node:path";
import fs from "node:fs";

/**
 * Supabase / cookie auth bootstrap for Playwright.
 * Adjust selectors to your app's login form.
 *
 * Requires E2E_EMAIL + E2E_PASSWORD in env (CI secrets).
 */
const authFile = path.join("playwright", ".auth", "user.json");

setup("authenticate", async ({ page }) => {
  const email = process.env.E2E_EMAIL;
  const password = process.env.E2E_PASSWORD;
  if (!email || !password) {
    setup.skip(true, "E2E_EMAIL / E2E_PASSWORD not set");
    return;
  }

  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  await page.goto("/login");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in|log in|continue/i }).click();

  // Wait for authenticated landing — adjust path for your app
  await expect(page).toHaveURL(/dashboard|app|home|projects/i, { timeout: 30_000 });

  await page.context().storageState({ path: authFile });
});
