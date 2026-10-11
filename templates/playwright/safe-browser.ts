import type { ConsoleMessage, Dialog, Download, Page, Request, Route } from "@playwright/test";

const DEFAULT_FORBIDDEN_QUERY_KEYS = [
  "authorization",
  "code",
  "cookie",
  "email",
  "key",
  "password",
  "secret",
  "session",
  "token",
];

export type BrowserGuardOptions = {
  allowedOrigins: string[];
  exactPageDerivedUrls?: string[];
  forbiddenQueryKeys?: string[];
  allowDownloads?: boolean;
  allowPopups?: boolean;
};

export type BrowserGuardEvidence = {
  navigations: string[];
  blockedRequests: Array<{ url: string; reason: string }>;
  unexpectedPopups: string[];
  unexpectedDownloads: string[];
  dialogs: Array<{ type: string; message: string }>;
  failedRequests: string[];
  consoleErrors: string[];
  pageErrors: string[];
};

export function redactBrowserUrl(rawUrl: string): string {
  try {
    const url = new URL(rawUrl);
    url.username = "";
    url.password = "";
    url.search = url.search ? "?%5Bredacted%5D" : "";
    url.hash = "";
    return url.href;
  } catch {
    return "[invalid URL]";
  }
}

export function inspectBrowserUrl(
  rawUrl: string,
  allowedOrigins: string[],
  forbiddenQueryKeys = DEFAULT_FORBIDDEN_QUERY_KEYS,
): string[] {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return ["invalid URL"];
  }
  const issues: string[] = [];
  if (!allowedOrigins.includes(url.origin)) issues.push(`origin not allowed: ${url.origin}`);
  const forbidden = new Set(forbiddenQueryKeys.map((key) => key.toLowerCase()));
  for (const key of url.searchParams.keys()) {
    if (forbidden.has(key.toLowerCase())) issues.push(`forbidden query key: ${key}`);
  }
  if (url.username || url.password) issues.push("URL contains userinfo credentials");
  return issues;
}

export async function installBrowserGuard(
  page: Page,
  options: BrowserGuardOptions,
): Promise<{ evidence: BrowserGuardEvidence; assertClean: () => void }> {
  if (!options.allowedOrigins.length) throw new Error("Browser guard requires at least one allowed origin");
  for (const candidate of options.allowedOrigins) {
    const parsed = new URL(candidate);
    if (parsed.origin !== candidate) throw new Error(`Allowed origin must be canonical: ${candidate}`);
  }

  const evidence: BrowserGuardEvidence = {
    navigations: [],
    blockedRequests: [],
    unexpectedPopups: [],
    unexpectedDownloads: [],
    dialogs: [],
    failedRequests: [],
    consoleErrors: [],
    pageErrors: [],
  };
  const exactUrls = new Set(options.exactPageDerivedUrls ?? []);
  const forbidden = options.forbiddenQueryKeys ?? DEFAULT_FORBIDDEN_QUERY_KEYS;

  await page.context().route("**/*", async (route: Route) => {
    const request = route.request();
    const issues = inspectBrowserUrl(request.url(), options.allowedOrigins, forbidden);
    if (request.isNavigationRequest() && exactUrls.size > 0 && !exactUrls.has(request.url())) {
      issues.push("navigation URL was not exact-allowlisted");
    }
    if (issues.length) {
      evidence.blockedRequests.push({ url: redactBrowserUrl(request.url()), reason: issues.join("; ") });
      await route.abort("blockedbyclient");
      return;
    }
    await route.continue();
  });

  page.on("framenavigated", (frame) => {
    if (frame === page.mainFrame()) evidence.navigations.push(redactBrowserUrl(frame.url()));
  });
  page.on("popup", async (popup: Page) => {
    evidence.unexpectedPopups.push(redactBrowserUrl(popup.url()));
    if (!options.allowPopups) await popup.close();
  });
  page.on("download", async (download: Download) => {
    evidence.unexpectedDownloads.push("[redacted filename]");
    if (!options.allowDownloads) await download.cancel();
  });
  page.on("dialog", async (dialog: Dialog) => {
    evidence.dialogs.push({ type: dialog.type(), message: "[redacted message]" });
    await dialog.dismiss();
  });
  page.on("requestfailed", (request: Request) => {
    if (request.failure()?.errorText !== "net::ERR_BLOCKED_BY_CLIENT") {
      evidence.failedRequests.push(`${request.method()} ${redactBrowserUrl(request.url())}: failed`);
    }
  });
  page.on("console", (message: ConsoleMessage) => {
    if (message.type() === "error") evidence.consoleErrors.push("[redacted console error]");
  });
  page.on("pageerror", () => evidence.pageErrors.push("[redacted page error]"));

  return {
    evidence,
    assertClean: () => {
      const failures = [
        ...evidence.blockedRequests.map((item) => `${item.reason} (${item.url})`),
        ...evidence.unexpectedPopups.map((url) => `unexpected popup: ${url}`),
        ...evidence.unexpectedDownloads.map((name) => `unexpected download: ${name}`),
        ...evidence.dialogs.map((item) => `unexpected ${item.type} dialog: ${item.message}`),
        ...evidence.failedRequests,
        ...evidence.consoleErrors,
        ...evidence.pageErrors,
      ];
      if (failures.length) throw new Error(`Browser guard violations:\n${failures.join("\n")}`);
    },
  };
}
