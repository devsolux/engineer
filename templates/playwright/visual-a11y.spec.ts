import AxeBuilder from "@axe-core/playwright";
import { test, expect } from "./fixtures";

const routeConfig = String(process.env.E2E_PUBLIC_ROUTES ?? "/,/login");
const routes = routeConfig
  .split(",")
  .map((route) => route.trim())
  .filter(Boolean);

for (const route of routes) {
  test(`${route} has no serious accessibility violations`, async ({ page }) => {
    await page.goto(route);
    await expect(page.getByRole("main")).toBeVisible();
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
      .analyze();
    expect(
      result.violations.filter((item: { impact?: string | null }) =>
        ["critical", "serious"].includes(item.impact ?? ""),
      ),
    ).toEqual([]);
  });
}
