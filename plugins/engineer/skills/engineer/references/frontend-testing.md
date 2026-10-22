# Frontend testing: Vitest, RTL, Playwright

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `backend-testing.md` | pgTAP, Server Action integration |
| `enforcement.md` | CI, a11y axe in pipeline |
| `frontend.md` | Component architecture under test |
| `templates/playwright/` | Dual public/auth E2E skeleton |

## Contents
- [What to test where](#what-to-test-where)
- [Playwright templates (copy into app)](#playwright-templates-copy-into-app)
- [React Testing Library rules](#react-testing-library-rules)
- [Mocking server/API](#mocking-serverapi)
- [Playwright E2E](#playwright-e2e)
- [Server Component testing](#server-component-testing)
- [CI checklist](#ci-checklist)
- [Anti-patterns](#anti-patterns)

Testing pyramid for Next.js App Router apps:

```
 E2E (Playwright) <- 5-15 critical user flows
 / \
 Integration (RTL) <- forms, auth, key interactions
 / \
Unit (Vitest) <- pure utils, schemas, hooks logic
```

| Layer | Count guidance | CI |
|---|---|---|
| Unit | Many, ms each | Every PR |
| Integration | Moderate | Every PR |
| E2E | Few, stable selectors | Every PR (chromium); full browsers nightly optional |
| Exploratory | Unlimited | gstack `/qa` on preview, not CI |

**Do not invert the pyramid** (hundreds of E2E, zero units). Flaky E2E without unit coverage is a tax.

## What to test where

| Layer | Tool | Examples |
|---|---|---|
| Zod schemas, formatters | Vitest unit | `profileSchema`, `formatCurrency` |
| Form validation UX | RTL integration | error on blur, submit disabled |
| Server Actions | RTL + mock Supabase | auth gate, validation errors |
| Critical flows | Playwright E2E | signup, checkout, settings save |
| Visual regression | Storybook/Chromatic (optional) | token changes, component states |
| a11y smoke | axe in Playwright or Storybook | critical pages |

## Playwright templates (copy into app)

Ready-made fail-closed lane projects live in **`templates/playwright/`**:

| Piece | Role |
|---|---|
| `playwright.config.ts` | desktop/mobile public + auth + quality projects; optional local webServer |
| `auth.setup.ts` | Login once → `playwright/.auth/user.json` (Supabase cookie style) |
| `public/smoke.spec.ts` | Unauth marketing / login reachable |
| `auth/read/app.spec.ts` | Parallel-safe logged-in dashboard/settings skeleton |
| `auth/write/*.spec.ts` | App-authored (none shipped); explicit single-worker shared-account mutations |
| `fixtures.ts` | per-worker test namespace for isolated data |
| `safe-browser.ts` | enforce browser-agent origins, secret-free URLs, and unexpected-event evidence |
| `visual-a11y.spec.ts` | axe WCAG 2.2 AA serious/critical gate |
| `mobile-quality.spec.ts` | 320px document reflow plus viewport and zoom policy gate |
| `network-console.spec.ts` | uncaught errors + failed first-party request gate |

For a reviewed parallel preview/staging schedule, start from
`templates/agentic/playwright-lane-plan.sample.json` and use `scripts/run-browser-lanes.py`; see
`browser-qa.md`. Keep raw execution evidence separate from reviewed browser-session receipts.

```bash
export ENGINEER=/path/to/engineer
mkdir -p e2e
# Follow templates/playwright/README.md: config at app root, specs under e2e/.
cp "$ENGINEER/templates/playwright/playwright.config.ts" ./
cp -R "$ENGINEER/templates/playwright/auth" "$ENGINEER/templates/playwright/public" e2e/
pnpm add -D @playwright/test @axe-core/playwright && pnpm exec playwright install chromium
```

Copy the root-level setup, fixtures, and quality specs listed in the template README.
Do not copy the entire template directory into `e2e/`; that creates `e2e/e2e`.

**Compose with gstack:** Playwright owns **CI-critical paths**; gstack `/qa` + `/browse` own exploratory dogfooding on a live preview. Do not replace one with the other.

Env for auth project: `E2E_EMAIL`, `E2E_PASSWORD`, `BASE_URL`. Never commit `playwright/.auth/`.

## React Testing Library rules

Query priority (accessible first):

1. `getByRole`
2. `getByLabelText`
3. `getByPlaceholderText` (labels preferred), then `getByText`, `getByDisplayValue`, `getByAltText`, `getByTitle`
4. Never `getByTestId` unless no accessible alternative

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProfileForm } from "./profile-form";

it("shows validation error on blur", async () => {
 const user = userEvent.setup();
 render(<ProfileForm />);

 const email = screen.getByLabelText(/email/i);
 await user.type(email, "not-an-email");
 await user.tab(); // blur

 expect(await screen.findByRole("alert")).toHaveTextContent(/valid email/i);
});
```

- Use `userEvent` not `fireEvent`
- `findBy*` for async; `waitFor` sparingly
- Test behavior users see, not implementation details

## Mocking server/API

**MSW** 3 (Node >= 22.12) for HTTP boundaries in integration tests; 2.x imports `http`/`HttpResponse` from `msw`:

```typescript
import { http, HttpResponse } from "msw/http";
import { setupServer } from "msw/node";

const server = setupServer(
 http.get("/api/projects", () =>
 HttpResponse.json([{ id: "1", name: "Alpha" }])
 )
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

For Server Actions: test the action function directly with mocked Supabase client.

## Playwright E2E

Focus on **critical paths only** - full suite gets slow and flaky.

```typescript
// e2e/signup.spec.ts
import { test, expect } from "@playwright/test";

test("user can sign up and land on dashboard", async ({ page }) => {
 await page.goto("/signup");
 await page.getByLabel("Email").fill("test@example.com");
 await page.getByLabel("Password").fill("secure-password-123");
 await page.getByRole("button", { name: /create account/i }).click();
 await expect(page).toHaveURL("/dashboard");
 await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible();
});
```

Best practices:
- `getByRole`, `getByLabel` - same a11y-first queries as RTL
- Seed test data or use isolated test project (Supabase branch)
- Run against preview deploys in CI
- Avoid `page.waitForTimeout` - use `expect` auto-wait
- Public and authenticated read lanes may run parallel; shared-account writes belong only in `auth/write` and require `E2E_LANE=auth-write`
- Use a unique tenant/user/data namespace per worker for mutating tests
- Retain trace/video/screenshots on failure, not on every green run
- Fail critical routes on uncaught page errors and first-party request failures
- Automated axe checks catch only some accessibility failures; keep keyboard, screen-reader, zoom, and inclusive manual testing
- Auth projects are conditional on both E2E credentials, so unauthenticated local runs do not fail on a missing storage-state file
- Standard runs exclude `auth/write`; the explicit write lane forces one worker and disables full parallelism
- Remote preview URLs skip the local `pnpm dev` web server automatically

Full lane and evidence rules: `browser-qa.md`.

## Server Component testing

Vitest does not support async Server Components (Next.js docs); sync Server and Client Components can be unit-tested. Options:

1. **Test the leaf** - extract pure logic to testable functions
2. **Integration via E2E** - full render path in Playwright
3. **Test data loaders** - unit test async functions that fetch/transform

Don't fight RSC in unit tests - test at the right boundary.

## CI checklist

- [ ] Vitest on every PR (schemas, utils, client components)
- [ ] RTL on forms and interactive components
- [ ] Playwright on 5-15 smoke flows (staging)
- [ ] a11y lint: eslint-plugin-jsx-a11y in CI (6.10.2 peers ESLint <= 9; confirm before ESLint 10)
- [ ] Optional: axe in Playwright for critical pages

## Anti-patterns

- Testing implementation (`useState` call counts, private methods)
- Snapshot-only tests with no behavior assertion
- E2E for every edge case (unit/integration first)
- `getByTestId` everywhere
- Flaky tests with fixed timeouts instead of assertions
- Skipping error/empty/loading state tests

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
