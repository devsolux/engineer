#!/usr/bin/env bash
# Consumer fixture for the Playwright template install and config behavior.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
APP="$TMP/app"
mkdir -p "$APP/e2e/auth/read" "$APP/e2e/auth/write" "$APP/e2e/public"
touch "$APP/.gitignore"

# Keep this installation sequence aligned with templates/playwright/README.md.
cp "$ROOT/templates/playwright/playwright.config.ts" "$APP/"
cp "$ROOT/templates/playwright/auth.setup.ts" \
   "$ROOT/templates/playwright/fixtures.ts" \
   "$ROOT/templates/playwright/safe-browser.ts" \
   "$ROOT/templates/playwright/visual-a11y.spec.ts" \
   "$ROOT/templates/playwright/mobile-quality.ts" \
   "$ROOT/templates/playwright/mobile-quality.spec.ts" \
   "$ROOT/templates/playwright/network-console.spec.ts" "$APP/e2e/"
cp "$ROOT/templates/playwright/auth/read/"*.ts "$APP/e2e/auth/read/"
cp "$ROOT/templates/playwright/public/"*.ts "$APP/e2e/public/"
cat "$ROOT/templates/playwright/gitignore.snippet" >> "$APP/.gitignore"

echo "engineer test-playwright-template — consumer fixture"
echo "---"
grep -Fq 'cp "$ENGINEER/templates/playwright/playwright.config.ts" ./' "$ROOT/templates/playwright/README.md"
if grep -Eq 'cp -R .*templates/playwright/.+ e2e/' "$ROOT/templates/playwright/README.md"; then
  echo "  ✗ README still documents copying the root config under e2e"
  exit 1
fi
test -f "$APP/playwright.config.ts"
test -f "$APP/e2e/auth.setup.ts"
test -f "$APP/e2e/auth/read/app.spec.ts"
test -f "$APP/e2e/public/smoke.spec.ts"
test -f "$APP/e2e/mobile-quality.spec.ts"
test -f "$APP/e2e/mobile-quality.ts"
test ! -d "$APP/e2e/e2e"
grep -q 'testDir: "./e2e"' "$APP/playwright.config.ts"
grep -q '^playwright/\.auth/' "$APP/.gitignore"
grep -q '^test-results/' "$APP/.gitignore"
echo "  ✓ README and consumer install layout agree; evidence paths are ignored"

cat > "$APP/stubs.d.ts" <<'DTS'
declare module "@playwright/test" {
  interface BrowserContext {
    route(pattern: string, callback: (route: Route) => Promise<void>): Promise<void>;
    storageState(options: { path: string }): Promise<void>;
  }
  interface Frame { url(): string; }
  interface Route { request(): Request; abort(code?: string): Promise<void>; continue(): Promise<void>; }
  interface Request { url(): string; frame(): Frame; isNavigationRequest(): boolean; failure(): { errorText?: string } | null; method(): string; }
  interface Download { suggestedFilename(): string; cancel(): Promise<void>; }
  interface Dialog { type(): string; message(): string; dismiss(): Promise<void>; }
  interface ConsoleMessage { type(): string; text(): string; }
  interface Page {
    [key: string]: any;
    context(): BrowserContext;
    mainFrame(): Frame;
    url(): string;
    close(): Promise<void>;
    on(event: string, callback: (value: any) => any): void;
  }
  interface TestArgs { page: Page; baseURL?: string; }
  interface TestCallable {
    (name: string, fn: (args: TestArgs, testInfo: any) => any): void;
    describe: { (name: string, fn: () => void): void; configure(options: any): void };
    skip(condition?: boolean, description?: string): void;
    extend<T, U>(fixtures: Record<string, [
      (args: TestArgs, use: (value?: any) => Promise<void>, info: any) => Promise<void>,
      Record<string, any>
    ]>): TestCallable;
  }
  export const test: TestCallable;
  export const expect: any;
  export const devices: Record<string, any>;
  export function defineConfig(config: any): any;
}
declare module "@axe-core/playwright" {
  export default class AxeBuilder {
    constructor(options: any);
    withTags(tags: string[]): this;
    analyze(): Promise<{ violations: Array<{ impact?: string | null }> }>;
  }
}
declare module "node:path" { const value: any; export default value; }
declare module "node:fs" { const value: any; export default value; }
declare const process: { env: Record<string, string | undefined> };
declare const Buffer: { from(value: string): any };
DTS

if command -v tsc >/dev/null 2>&1; then
  tsc --noEmit --strict --skipLibCheck --moduleResolution bundler --module esnext \
    --target es2022 --allowSyntheticDefaultImports "$APP/stubs.d.ts" \
    "$APP/playwright.config.ts" "$APP/e2e/auth.setup.ts" "$APP/e2e/fixtures.ts" \
    "$APP/e2e/safe-browser.ts" \
    "$APP/e2e/visual-a11y.spec.ts" "$APP/e2e/mobile-quality.ts" \
    "$APP/e2e/mobile-quality.spec.ts" \
    "$APP/e2e/network-console.spec.ts" \
    "$APP/e2e/auth/read/app.spec.ts" "$APP/e2e/public/smoke.spec.ts"
  echo "  ✓ installed TypeScript compiles against Playwright-compatible contracts"
else
  echo "  ⚠ tsc unavailable; skipped template type fixture"
fi

tsc --skipLibCheck --moduleResolution node16 --module node16 --target es2022 \
  --allowSyntheticDefaultImports --outDir "$TMP/safe-dist" "$APP/stubs.d.ts" "$APP/e2e/safe-browser.ts"
node - "$TMP/safe-dist/safe-browser.js" <<'JS'
const safe = require(process.argv[2]);
const allowed = ["https://preview.example.test"];
if (safe.inspectBrowserUrl("https://preview.example.test/dashboard", allowed).length) throw new Error("safe URL rejected");
if (!safe.inspectBrowserUrl("https://evil.example/", allowed).some((x) => x.includes("origin not allowed"))) throw new Error("external origin accepted");
if (!safe.inspectBrowserUrl("https://preview.example.test/?token=synthetic", allowed).some((x) => x.includes("forbidden query key"))) throw new Error("secret query accepted");
if (!safe.inspectBrowserUrl("https://user:pass@preview.example.test/", allowed).some((x) => x.includes("userinfo"))) throw new Error("URL credentials accepted");
const redacted = safe.redactBrowserUrl("https://user:pass@preview.example.test/private?token=secret#fragment");
if (redacted.includes("user") || redacted.includes("pass") || redacted.includes("secret") || redacted.includes("fragment")) throw new Error("browser evidence URL leaked sensitive values");
if (!redacted.includes("redacted")) throw new Error("browser evidence URL was not marked redacted");
JS
echo "  ✓ browser guard rejects unsafe URLs and redacts persisted URL evidence"

grep -Fq 'from "../fixtures"' "$APP/e2e/public/smoke.spec.ts"
grep -Fq 'from "../../fixtures"' "$APP/e2e/auth/read/app.spec.ts"
grep -Fq 'from "./fixtures"' "$APP/e2e/mobile-quality.spec.ts"
grep -Fq 'from "./mobile-quality"' "$APP/e2e/mobile-quality.spec.ts"
grep -Fq 'quality.scrollWidth' "$APP/e2e/mobile-quality.spec.ts"
grep -Fq 'testInfo.attach("engineer-browser-evidence"' "$APP/e2e/fixtures.ts"
grep -Fq '{ auto: true }' "$APP/e2e/fixtures.ts"
echo "  ✓ all shipped browser specs use the automatic guarded evidence fixture"

tsc --skipLibCheck --moduleResolution node16 --module node16 --target es2022 \
  --outDir "$TMP/mobile-dist" "$APP/e2e/mobile-quality.ts"
node - "$TMP/mobile-dist/mobile-quality.js" <<'JS'
const { viewportQualityIssues } = require(process.argv[2]);
const pass = [
  "width=device-width, initial-scale=1",
  "width = device-width; user-scalable = yes; maximum-scale = 2",
  "width=device-width,maximum-scale=-1",
];
for (const value of pass) {
  if (viewportQualityIssues(value).length) throw new Error(`valid viewport rejected: ${value}`);
}
const fail = [
  null,
  "width=980",
  "width=device-width,user-scalable=no",
  "width=device-width;user-scalable=0",
  "width=device-width;user-scalable=0.0",
  "width=device-width,maximum-scale=1.5",
  "width=device-width,maximum-scale=yes",
  "width=device-width,maximum-scale=invalid",
  "width=device-width,width=980",
];
for (const value of fail) {
  if (!viewportQualityIssues(value).length) throw new Error(`unsafe viewport accepted: ${value}`);
}
JS
echo "  ✓ viewport policy parser accepts usable variants and rejects restrictive or ambiguous input"

mkdir -p "$APP/node_modules/@playwright/test" "$TMP/dist"
cat > "$APP/node_modules/@playwright/test/index.js" <<'JS'
exports.defineConfig = (config) => config;
exports.devices = { "Desktop Chrome": {}, "iPhone 13": {} };
JS

tsc --skipLibCheck --moduleResolution node16 --module node16 --target es2022 \
  --allowSyntheticDefaultImports --outDir "$TMP/dist" "$APP/stubs.d.ts" "$APP/playwright.config.ts"
CONFIG="$TMP/dist/playwright.config.js"

env -u CI -u E2E_EMAIL -u E2E_PASSWORD -u BASE_URL \
  NODE_PATH="$APP/node_modules" node -e '
    const c = require(process.argv[1]).default;
    const names = c.projects.map((p) => p.name);
    for (const n of ["public-desktop", "public-mobile", "quality-desktop", "quality-mobile", "quality-compact"])
      if (!names.includes(n)) throw new Error(`missing ${n}`);
    if (names.includes("setup") || names.some((n) => n.startsWith("auth-"))) throw new Error("auth projects should be conditional");
    if (c.testDir !== "./e2e") throw new Error(`bad testDir ${c.testDir}`);
    if (!c.webServer) throw new Error("local URL should start the dev server");
  ' "$CONFIG"
echo "  ✓ public/quality projects and local server behavior"

E2E_EMAIL=test@example.test E2E_PASSWORD=fixture NODE_PATH="$APP/node_modules" node -e '
  const names = require(process.argv[1]).default.projects.map((p) => p.name);
  if (!names.includes("setup") || !names.includes("auth-read-desktop")) throw new Error("auth read projects missing");
  if (names.includes("auth-write-serial")) throw new Error("standard lane must exclude auth writes");
' "$CONFIG"
echo "  ✓ standard lane includes auth reads and excludes shared-account writes"

E2E_LANE=auth-write E2E_EMAIL=test@example.test E2E_PASSWORD=fixture NODE_PATH="$APP/node_modules" node -e '
  const c = require(process.argv[1]).default;
  const names = c.projects.map((p) => p.name);
  if (names.join(",") !== "setup,auth-write-serial") throw new Error(`unexpected write lane: ${names}`);
  if (c.workers !== 1 || c.fullyParallel !== false) throw new Error("auth writes must be single-worker serial");
' "$CONFIG"
echo "  ✓ explicit auth-write lane is fail-closed and serial"

if E2E_LANE=auth-write NODE_PATH="$APP/node_modules" node -e 'require(process.argv[1])' "$CONFIG" >/dev/null 2>&1; then
  echo "  ✗ auth-write lane accepted missing credentials"
  exit 1
fi
if E2E_LANE=typo NODE_PATH="$APP/node_modules" node -e 'require(process.argv[1])' "$CONFIG" >/dev/null 2>&1; then
  echo "  ✗ invalid E2E_LANE was accepted"
  exit 1
fi
if E2E_OUTPUT_DIR=../../outside NODE_PATH="$APP/node_modules" node -e 'require(process.argv[1])' "$CONFIG" >/dev/null 2>&1; then
  echo "  ✗ unsafe E2E_OUTPUT_DIR was accepted"
  exit 1
fi
echo "  ✓ invalid or unauthenticated lane selection rejected"

BASE_URL=https://preview.example.test NODE_PATH="$APP/node_modules" node -e '
  const c = require(process.argv[1]).default;
  if (c.webServer) throw new Error("remote URL must not start local web server");
' "$CONFIG"
echo "  ✓ remote preview skips local web server"

if CI=1 E2E_WORKERS=invalid NODE_PATH="$APP/node_modules" node -e \
  'require(process.argv[1])' "$CONFIG" >/dev/null 2>&1; then
  echo "  ✗ invalid E2E_WORKERS was accepted"
  exit 1
fi
echo "  ✓ invalid worker configuration rejected"

echo "---"
echo "OK — Playwright template consumer contract passed"
