import { expect, test } from "./fixtures";
import { viewportQualityIssues } from "./mobile-quality";

const routes = String(process.env.E2E_PUBLIC_ROUTES ?? "/,/login")
  .split(",")
  .map((route) => route.trim())
  .filter(Boolean);

for (const route of routes) {
  test(`${route} preserves compact mobile reflow and zoom`, async ({ page }) => {
    await page.goto(route);
    await expect(page.getByRole("main")).toBeVisible();

    const quality = await page.evaluate(() => {
      const root = document.documentElement;
      const viewport = document
        .querySelector<HTMLMetaElement>('meta[name="viewport" i]')
        ?.content.toLowerCase();

      return {
        clientWidth: root.clientWidth,
        scrollWidth: root.scrollWidth,
        viewport: viewport ?? null,
      };
    });

    expect(viewportQualityIssues(quality.viewport)).toEqual([]);

    expect(
      quality.scrollWidth,
      `document overflows compact viewport by ${quality.scrollWidth - quality.clientWidth}px`,
    ).toBeLessThanOrEqual(quality.clientWidth + 1);
  });
}
