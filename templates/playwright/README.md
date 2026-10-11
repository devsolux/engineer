# Playwright templates (engineer)

Copy into the **target app**, not into this skill package as a runtime dependency.

```bash
# from app root
cp "$ENGINEER/templates/playwright/playwright.config.ts" ./
mkdir -p e2e/auth/read e2e/auth/write e2e/public
cp "$ENGINEER/templates/playwright/auth.setup.ts" \
   "$ENGINEER/templates/playwright/fixtures.ts" \
   "$ENGINEER/templates/playwright/safe-browser.ts" \
   "$ENGINEER/templates/playwright/visual-a11y.spec.ts" \
   "$ENGINEER/templates/playwright/mobile-quality.ts" \
   "$ENGINEER/templates/playwright/mobile-quality.spec.ts" \
   "$ENGINEER/templates/playwright/network-console.spec.ts" e2e/
cp "$ENGINEER/templates/playwright/auth/read/"*.ts e2e/auth/read/
cp "$ENGINEER/templates/playwright/public/"*.ts e2e/public/
cat "$ENGINEER/templates/playwright/gitignore.snippet" >> .gitignore
pnpm add -D @playwright/test @axe-core/playwright
pnpm exec playwright install chromium
```

`playwright.config.ts` belongs at the app root. Putting the whole template
directory under `e2e/` makes its `testDir: "./e2e"` resolve to `e2e/e2e`.

## Layout

| File | Role |
|---|---|
| `playwright.config.ts` | Root config for desktop/mobile public, auth, and quality projects |
| `auth.setup.ts` | Logs in once → writes `playwright/.auth/user.json` |
| `public/smoke.spec.ts` | Marketing / unauth routes |
| `auth/read/app.spec.ts` | Parallel-safe logged-in read path |
| `auth/write/*.spec.ts` | Shared-account mutations; only via the serial lane |
| `fixtures.ts` | Per-worker namespace plus automatic guarded evidence attachment |
| `safe-browser.ts` | Origin, secret-URL, popup, download, dialog, request, and error guard |
| `visual-a11y.spec.ts` | axe WCAG 2.2 AA serious/critical gate |
| `mobile-quality.spec.ts` | 320px reflow, page overflow, device-width viewport, and zoom gate |
| `mobile-quality.ts` | Deterministic viewport policy parser used by the mobile spec |
| `network-console.spec.ts` | Uncaught error + failed first-party request gate |
| `gitignore.snippet` | Ignore auth state, reports, and test evidence |

## Compose with gstack

- **engineer** owns *what* to cover, lane isolation, fixtures, and CI evidence.
- **gstack `/qa` or `/browse`** owns exploratory browser dogfooding on a running app.
- Do not duplicate exploratory visual QA inside Playwright unless the regression is stable and CI-critical.

## Parallel safety

- Public read-only routes may run fully parallel.
- Use `testNamespace` (stable `parallelIndex`) for any records created by a worker.
- Put shared-account mutations only under `e2e/auth/write/` and run them with `E2E_LANE=auth-write`; the config forces one worker and disables full parallelism.
- The default `standard` lane excludes `auth/write`, so a general test run cannot accidentally parallelize shared-account mutations.
- Never point mutating suites at production.
- Generic CI defaults to one worker. Set `E2E_WORKERS` only with isolated test data, or shard independent projects across CI jobs.
- Auth projects appear only when both `E2E_EMAIL` and `E2E_PASSWORD` exist. An explicit CI auth command therefore fails clearly if secrets are missing.
- Remote `BASE_URL` values do not start `pnpm dev`. Set `E2E_NO_WEBSERVER=1` to disable the local server for another local runner.

## CI sketch

```yaml
- run: pnpm exec playwright test --project=public-desktop --project=public-mobile --project=quality-desktop --project=quality-mobile --project=quality-compact
- run: pnpm exec playwright test
  env:
    E2E_LANE: auth-read
    E2E_EMAIL: ${{ secrets.E2E_EMAIL }}
    E2E_PASSWORD: ${{ secrets.E2E_PASSWORD }}
    BASE_URL: ${{ vars.PREVIEW_URL }}
- run: pnpm exec playwright test
  env:
    E2E_LANE: auth-write
    E2E_EMAIL: ${{ secrets.E2E_EMAIL }}
    E2E_PASSWORD: ${{ secrets.E2E_PASSWORD }}
    BASE_URL: ${{ vars.PREVIEW_URL }}
```

Never commit real credentials. Prefer dedicated E2E user + seed script.

## Multi-lane preview runner

Copy `templates/agentic/playwright-lane-plan.sample.json` to `.engineer/browser-plan.json`, set a unique
run ID, canonical preview/staging origin, enabled lanes, and matching immutable output root. Review
the compiled commands first, then execute. Authenticated lanes currently use one worker because this
template's setup project creates one shared storage-state file; add Playwright's per-worker auth
fixture before raising that limit.

The runner uses Playwright's JSON reporter and unique output directories. Its execution receipt is raw
capture evidence only; validate it, then compile and independently review the browser-session and
aggregate lane receipts before promotion.

All shipped specs import the local `fixtures.ts`, which installs the origin/request/browser guard
before navigation and attaches `engineer-browser-evidence` JSON during teardown, including failed tests.
Persisted URLs remove credentials, query values, and fragments; filenames, dialogs, console errors,
page errors, and request failure text are minimized before attachment. The attachment records observed
guard events, not action intent, approvals, cleanup truth, account ownership, or reviewer judgment.

The compact quality project checks document-level reflow at 320 CSS pixels and rejects viewport
settings that disable zoom or cap it below 200%. Contained two-dimensional widgets such as maps,
code blocks, and data tables may keep their own labeled scroll region; the page itself must not
overflow. Emulation does not prove virtual-keyboard behavior, browser chrome, safe-area handling,
physical touch ergonomics, thermal constraints, or real-device performance. Keep the real iOS and
Android pass in the release matrix.

## Agent-controlled browser guard

Install the guard before the first navigation in exploratory or agent-authored tests:

```typescript
const guard = await installBrowserGuard(page, {
  allowedOrigins: [new URL(baseURL!).origin],
  exactPageDerivedUrls: [new URL("/", baseURL).href],
});

await page.goto("/");
// assertions and observations
guard.assertClean();
```

The guard blocks requests outside declared origins and URLs with sensitive query keys. It records
unexpected popups, downloads, dialogs, failed requests, console errors, and page errors. Keep
mutation approval and prompt-injection decisions in the browser-session receipt; a page event hook
cannot determine user intent by itself.
