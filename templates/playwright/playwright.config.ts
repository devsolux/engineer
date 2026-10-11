import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * engineer multi-lane Playwright config.
 * - standard: public, quality, and authenticated read-only lanes
 * - auth-write: explicit single-worker shared-account mutation lane
 *
 * Env: BASE_URL (default http://127.0.0.1:3000)
 */
const baseURL = process.env.BASE_URL ?? "http://127.0.0.1:3000";
const hasAuthCredentials = Boolean(process.env.E2E_EMAIL && process.env.E2E_PASSWORD);
const lane = process.env.E2E_LANE ?? "standard";
const outputDir = process.env.E2E_OUTPUT_DIR ?? "test-results/playwright";
if (path.isAbsolute(outputDir) || outputDir.split(/[\\/]+/).includes("..")) {
  throw new Error("E2E_OUTPUT_DIR must be a repository-relative confined path");
}
const lanes = new Set(["standard", "public", "quality", "auth-read", "auth-write"]);
if (!lanes.has(lane)) {
  throw new Error(`E2E_LANE must be one of ${[...lanes].join(", ")}, received: ${lane}`);
}
if ((lane === "auth-read" || lane === "auth-write") && !hasAuthCredentials) {
  throw new Error(`${lane} requires E2E_EMAIL and E2E_PASSWORD`);
}
const localHosts = new Set(["127.0.0.1", "localhost", "::1"]);
const shouldStartWebServer =
  !process.env.CI &&
  process.env.E2E_NO_WEBSERVER !== "1" &&
  localHosts.has(new URL(baseURL).hostname);

function ciWorkers(): number | undefined {
  if (!process.env.CI) return undefined;
  const raw = process.env.E2E_WORKERS ?? "1";
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`E2E_WORKERS must be a positive integer, received: ${raw}`);
  }
  return value;
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: lane !== "auth-write",
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // Playwright recommends one worker in generic CI for reproducibility.
  // Opt into more only on isolated, sufficiently provisioned runners; shard jobs for scale.
  workers: lane === "auth-write" ? 1 : ciWorkers(),
  reporter: process.env.CI ? "github" : "list",
  outputDir,
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    acceptDownloads: false,
    permissions: [],
    serviceWorkers: "block",
  },
  projects: [
    {
      name: "public-desktop",
      testMatch: /public\/.*\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "public-mobile",
      testMatch: /public\/.*\.spec\.ts/,
      use: { ...devices["iPhone 13"] },
    },
    {
      name: "quality-desktop",
      testMatch: /(visual-a11y|network-console)\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "quality-mobile",
      testMatch: /(visual-a11y|network-console|mobile-quality)\.spec\.ts/,
      use: { ...devices["iPhone 13"] },
    },
    {
      name: "quality-compact",
      testMatch: /mobile-quality\.spec\.ts/,
      use: {
        ...devices["iPhone 13"],
        viewport: { width: 320, height: 568 },
        screen: { width: 320, height: 568 },
      },
    },
    ...(hasAuthCredentials
      ? [
          {
            name: "setup",
            testMatch: /auth\.setup\.ts/,
          },
          {
            name: "auth-read-desktop",
            testMatch: /auth\/read\/.*\.spec\.ts/,
            dependencies: ["setup"],
            use: {
              ...devices["Desktop Chrome"],
              storageState: "playwright/.auth/user.json",
            },
          },
          {
            name: "auth-write-serial",
            testMatch: /auth\/write\/.*\.spec\.ts/,
            dependencies: ["setup"],
            use: {
              ...devices["Desktop Chrome"],
              storageState: "playwright/.auth/user.json",
            },
          },
        ]
      : []),
  ].filter((project) => {
    if (project.name === "setup") return lane === "standard" || lane.startsWith("auth-");
    if (lane === "standard") return project.name !== "auth-write-serial";
    if (lane === "public") return project.name.startsWith("public-");
    if (lane === "quality") return project.name.startsWith("quality-");
    return project.name === `${lane}-desktop` || project.name === "auth-write-serial" && lane === "auth-write";
  }),
  webServer: shouldStartWebServer
    ? {
        command: "pnpm dev",
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      }
    : undefined,
});
