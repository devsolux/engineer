import { test, expect } from "./fixtures";

test("home has no uncaught page errors or failed first-party requests", async ({ page, baseURL }) => {
  const pageErrors: string[] = [];
  const failedRequests: string[] = [];
  const baseOrigin = baseURL ? new URL(baseURL).origin : "";

  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    if (!baseOrigin || request.url().startsWith(baseOrigin)) {
      failedRequests.push(`${request.method()} ${request.url()} — ${request.failure()?.errorText ?? "failed"}`);
    }
  });

  await page.goto("/");
  await expect(page.getByRole("main")).toBeVisible();
  expect(pageErrors).toEqual([]);
  expect(failedRequests).toEqual([]);
});
