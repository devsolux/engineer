# Enforcement rules: the engineer rule catalog

**Last verified**: 2026-08-19 · **Review cadence**: 3 months
**Related**: `enforcement.md` (tiers, setup, CI wiring, maturity model)

The copy-paste rule catalog behind `enforcement.md`. Load this file when you need the exact
scanner rules, lint configs, grep gates, or rule→enforcement mappings; load `enforcement.md`
first for tier orientation and project setup.

## Contents
- [Rate-limit / abuse (scanner rules)](#rate-limit-abuse-scanner-rules)
- [engineer-scan (local policy grep)](#engineer-scan-local-policy-grep)
- [ESLint flat config (Next)](#eslint-flat-config-next)
- [Rule → enforcement map](#rule-enforcement-map)
- [ESLint configuration (copy-paste baseline)](#eslint-configuration-copy-paste-baseline)
- [Playwright a11y gate (copy-paste)](#playwright-a11y-gate-copy-paste)
- [Server Action auth grep (CI)](#server-action-auth-grep-ci)
- [Migration RLS gate](#migration-rls-gate)
- [RLS tests in CI (Supabase + pgTAP)](#rls-tests-in-ci-supabase-pgtap)
- [Secret scanning](#secret-scanning)

## Rate-limit / abuse (scanner rules)

`scripts/engineer-scan.sh --backend` (default on) warns when sensitive Server Actions
or mutation `route.ts` handlers lack a rate-limit call site. Under `--strict`,
missing limiters are **FAIL**.

| Detected surfaces | Expect |
|---|---|
| `"use server"` files with insert/update/delete/upsert | limiter call |
| Files matching deleteAccount, export*, signIn, password, checkout, … | limiter call |
| `POST|PUT|PATCH|DELETE` route handlers with those names | limiter call |
| `/api/**` subscribe/contact/newsletter routes | limiter (warn) |

**Accepted limiters (regex):** `rateLimit`, `ratelimit`, `limiter.limit`, `arcjet`,
`fixedWindow`, `slidingWindow`, `isRateLimited`, `checkRateLimit`.

**Exempt:** add a comment `// engineer:ratelimit-exempt` with a one-line reason
(e.g. internal-only admin action behind network policy).

PR checkbox: *Sensitive mutations have rate limits or documented exempt.*

## engineer-scan (local policy grep)

Runs from repo root. Categories:

| Flag | Checks |
|---|---|
| (default) | secrets, hardcoded colors, service role exposure |
| `--strict` | + `"use client"` on layouts, `getSession` in server files, missing `"use server"` auth patterns |
| `--design` | hardcoded Tailwind palette, `components/ui/` edits, AI-default gradient/indigo/glow, 3–4px card-stripe, 01–03 kicker, Inter-everywhere, and badge-above-H1 tells (WARN; FAIL under `--strict`) |
| `--backend` | RLS in migrations, webhook raw body, `updateTag` in route handlers |

Copy `scripts/engineer-scan.sh` into project or symlink from engineer install.

## ESLint flat config (Next)

Ship a root `eslint.config.mjs` and fail CI on warnings for app code:

```bash
# package.json
"lint:ci": "eslint . --max-warnings=0"
```

Template: **`templates/eslint.config.mjs`** (Next core-web-vitals + typescript via FlatCompat).

Local: husky/lint-staged optional. CI: run `lint:ci` on every PR with typecheck and `engineer-scan --strict`.

---

## Rule → enforcement map

### Design & frontend

| Rule | Enforce locally | Enforce CI |
|---|---|---|
| Semantic tokens only | engineer-scan `--design`; ESLint `no-restricted-syntax` | Same + visual review |
| WCAG labels/focus | `eslint-plugin-jsx-a11y` strict | `@axe-core/playwright` |
| `"use client"` at leaves | engineer-scan layout check | ESLint custom rule / grep |
| CWV | Lighthouse local | Lighthouse CI / Vercel checks |
| Form on-blur | RTL integration tests | Playwright form flows |

### Backend

| Rule | Enforce locally | Enforce CI |
|---|---|---|
| RLS on new tables | `check-rls-migration.sh` | pgTAP + migration review |
| `getUser()` on mutations | engineer-scan `--backend` | Custom grep in CI |
| Zod on inputs | ESLint / code review | Vitest schema tests |
| No service role in client | engineer-scan secrets | gitleaks + bundle analyze |
| Webhook signature | code review | Integration test with Stripe CLI |
| `updateTag` not in handlers | engineer-scan grep | CI grep |

### TypeScript & Rust

| Rule | Enforce locally | Enforce CI |
|---|---|---|
| `strict: true` | tsc | tsc in CI |
| No `any` | ESLint `@typescript-eslint/no-explicit-any` | `--max-warnings=0` |
| Rust no unwrap | clippy `deny(unwrap_used)` | `cargo clippy -- -D warnings` |

---

## ESLint configuration (copy-paste baseline)

Copy **`templates/eslint.config.mjs`** — it carries the full engineer enforcement
baseline. The load-bearing rules it enforces:

```javascript
// from templates/eslint.config.mjs (engineer enforcement baseline)
...jsxA11y.flatConfigs.recommended.rules,          // + label-has-associated-control: error
"@typescript-eslint/no-explicit-any": "error",
"no-restricted-imports": [...],                     // @/lib/supabase/admin is server-only
"no-restricted-syntax": [...],                      // no 'use client' on app/**/layout.tsx
```

Tighten `@typescript-eslint/no-unused-vars` from `warn` to `error` in mature apps.

### Tailwind hardcoded color ban (optional plugin)

Use `eslint-plugin-tailwindcss` or grep in engineer-scan for:
`text-(red|blue|green|gray|slate|zinc)-[0-9]` in `*.tsx` excluding `components/ui/`.

Prefer semantic classes: `text-destructive`, `bg-muted`, `text-foreground`.

---

## Playwright a11y gate (copy-paste)

```typescript
// e2e/a11y/critical-pages.spec.ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const CRITICAL_PATHS = ["/", "/login", "/dashboard"];

for (const path of CRITICAL_PATHS) {
 test(`a11y: ${path}`, async ({ page }) => {
 await page.goto(path);
 // Interact with dynamic UI before scan (accordions, tabs)
 const results = await new AxeBuilder({ page })
 .withTags(["wcag2a", "wcag2aa", "wcag22aa"])
 .analyze();
 expect(results.violations).toEqual([]);
 });
}
```

---

## Server Action auth grep (CI)

```bash
# Fail if "use server" file has DB mutation patterns but no getUser
for f in $(rg -l '"use server"' --glob '*.ts' --glob '*.tsx'); do
 if rg -q '\.(from|insert|update|delete|upsert)\(' "$f"; then
 if ! rg -q 'getUser\(\)|getCurrentUser' "$f"; then
 echo "FAIL: $f mutates data without getUser()"
 exit 1
 fi
 fi
done
```

False positives possible - allowlist with comment `// engineer:auth-exempt` + CODEOWNERS review.

---

## Migration RLS gate

Every `CREATE TABLE` in `supabase/migrations/` must be followed in same or
later migration by `ENABLE ROW LEVEL SECURITY` - or table is in private schema.

See `scripts/check-rls-migration.sh`.

---

## RLS tests in CI (Supabase + pgTAP)

```yaml
 rls:
 runs-on: ubuntu-latest
 steps:
 - uses: actions/checkout@v7
 - uses: supabase/setup-cli@v1
 - run: supabase start
 - run: supabase db reset
 - run: supabase test db # runs supabase/tests/*.sql
```

Example pgTAP test (`supabase/tests/rls_projects.test.sql`):

Full patterns and test matrix: `references/backend-testing.md`
Copy template: `templates/supabase/tests/rls_projects.test.sql`

---

## Secret scanning

Enable GitHub **secret scanning** + **push protection**. Add gitleaks locally:

```yaml
 - uses: gitleaks/gitleaks-action@v2
 env:
 GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Block patterns in engineer-scan:
- `SUPABASE_SERVICE_ROLE` in non-server files
- `sk_live_`, `sk_test_` in any tracked file
- `NEXT_PUBLIC_.*SERVICE.*ROLE`

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
