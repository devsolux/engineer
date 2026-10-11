import { test as base, expect } from "@playwright/test";
import { installBrowserGuard } from "./safe-browser";

type TestFixtures = {
  browserEvidence: void;
};

type WorkerFixtures = {
  testNamespace: string;
};

/**
 * Unique namespace for records created by parallel workers.
 * Use it in seeded email/account/project identifiers and delete only matching data.
 */
export const test = base.extend<TestFixtures, WorkerFixtures>({
  browserEvidence: [
    async ({ page, baseURL }, use, testInfo) => {
      if (!baseURL) throw new Error("Guarded browser evidence requires baseURL");
      const guard = await installBrowserGuard(page, { allowedOrigins: [new URL(baseURL).origin] });
      try {
        await use();
      } finally {
        await testInfo.attach("engineer-browser-evidence", {
          body: Buffer.from(JSON.stringify({ schema_version: 1, evidence: guard.evidence })),
          contentType: "application/json",
        });
        guard.assertClean();
      }
    },
    { auto: true },
  ],
  testNamespace: [
    async ({}, use, workerInfo) => {
      // parallelIndex is stable when Playwright restarts a failed worker.
      await use(`e2e-${workerInfo.project.name}-${workerInfo.parallelIndex}`);
    },
    { scope: "worker" },
  ],
});

export { expect };
