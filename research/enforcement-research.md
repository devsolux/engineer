# Enforcement research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `enforcement.md`, `code-quality.md`, all domain modules

## Executive summary

Best practices that aren't enforced become suggestions. 2026 fullstack teams use:

1. **Four enforcement tiers** — process → local → CI → production observability
2. **Policy-as-code** — grep scanners, ESLint, pgTAP, axe Playwright — not honor system
3. **Fail closed** — CI with `--max-warnings=0`; block merge on RLS/a11y/security scans
4. **Defense in depth** — static lint catches ~30% of a11y issues; axe runtime catches rest
5. **Migration gates** — every `CREATE TABLE public.*` must have RLS enable in migrations
6. **Server Action grep** — `"use server"` + DB mutation must have `getUser()` pattern
7. **Secret scanning** — gitleaks + never `NEXT_PUBLIC_*` for server keys

---

## 1. Why enforcement tiers matter

| Tier | Latency | Catches |
|---|---|---|
| Process (PR template, CODEOWNERS) | Human speed | Architecture mistakes, missing RLS review |
| Local (pre-commit) | Seconds | Format, lint, policy grep before push |
| CI | Minutes | Full test suite, a11y axe, pgTAP, build |
| Production | Hours/days | CWV regression, auth anomalies, webhook failures |

**Anti-pattern**: Only Tier 0 (checklist). Developers skip under pressure.

**Target maturity**: Greenfield SaaS L2 before launch; L3 before payments.

---

## 2. Accessibility enforcement

**Sources**: eslint-plugin-jsx-a11y, @axe-core/playwright, WCAG 2.2, AccessProof Next.js guide, a11y-next-app (2026)

### Three layers

| Layer | Tool | What it catches |
|---|---|---|
| Static | eslint-plugin-jsx-a11y | Missing alt, label, invalid ARIA, keyboard handlers |
| Runtime CI | @axe-core/playwright | Contrast, focus order, dynamic DOM after interaction |
| Manual | Keyboard-only pass | Focus trap bugs axe misses in modals |

### Key rules to escalate to error in CI

- `jsx-a11y/label-has-associated-control`: error
- `jsx-a11y/click-events-have-key-events`: error
- `jsx-a11y/no-static-element-interactions`: error
- `jsx-a11y/anchor-is-valid`: error

### Playwright axe pattern (2026)

1. Navigate to critical paths
2. **Interact first** — expand accordions, open modals, fill partial forms
3. Run `AxeBuilder` with `wcag2aa` + `wcag22aa` tags
4. Fail on any violation — zero tolerance on critical paths

### What lint cannot catch

- Contrast ratios (needs computed styles)
- Dynamic content after hydration
- Focus management in client islands
- Heading order across Server + Client composition

→ axe Playwright required for compliance confidence.

---

## 3. Design token enforcement

**Sources**: engineer design-system.md, Tailwind v4 @theme docs

### Grep patterns (engineer-scan)

Block in app code (exclude `components/ui/`):
- `text-{palette}-{50-950}`
- `bg-{palette}-{50-950}`

Allow semantic: `text-foreground`, `bg-muted`, `text-destructive`, `border-border`

### ESLint alternative

`no-restricted-syntax` or custom eslint-plugin for className strings.

### CI contrast (advanced)

- Style Dictionary token export → contrast checker script
- Fail if semantic pairs below 4.5:1 / 3:1 thresholds

---

## 4. Backend / RLS enforcement

**Sources**: Supabase docs, MakerKit RLS guide, pgTAP, Supabase CLI test

### Migration gate

Every `CREATE TABLE public.X` requires `ALTER TABLE public.X ENABLE ROW LEVEL SECURITY`
in same or subsequent migration file.

Automate: `scripts/check-rls-migration.sh`

### pgTAP integration

```bash
supabase test db   # runs supabase/tests/*.sql
```

Test matrix per table:
- anon cannot read private rows
- user A cannot read user B rows
- user can CRUD own rows
- service_role bypasses (documented admin-only)

### Policy code review checklist (human gate)

- [ ] USING + WITH CHECK on UPDATE
- [ ] `(select auth.uid())` not bare `auth.uid()`
- [ ] Indexed filter columns
- [ ] `TO authenticated` specified

---

## 5. Server Action security enforcement

**Sources**: Next.js docs, MakerKit secure actions, DigitalApplied 2026, Adamarant advisories

### Framework-provided (do not re-implement)

- POST-only
- Origin vs Host CSRF check
- Encrypted action IDs

### Must enforce in code + CI

| Check | Method |
|---|---|
| Zod on input | ESLint/review + Vitest |
| getUser() before mutate | engineer-scan --strict grep |
| Rate limit on sensitive | Code review + integration test |
| No secrets in return | Review + TypeScript |

### Grep logic

For each file with `"use server"` containing `.from(` / `.insert(` / `.update(`:
must contain `getUser()` or `getCurrentUser()` unless `// engineer:auth-exempt` with CODEOWNERS approval.

### allowedOrigins

Audit `next.config` on every deploy — reverse proxy misconfig breaks CSRF protection.

---

## 6. Webhook enforcement

| Rule | Enforcement |
|---|---|
| Raw body before verify | grep: no `req.json()` before constructEvent in webhook routes |
| Signature verify | Stripe CLI test in CI: `stripe trigger checkout.session.completed` |
| Idempotency | Unit test: process same event.id twice → single side effect |
| 500 on failure | Integration test asserts retry behavior |

---

## 7. Cache invalidation enforcement

| Rule | grep |
|---|---|
| No updateTag in route handlers | engineer-scan |
| cacheLife on use cache | Review + optional AST lint |
| Tag registry maintained | CODEOWNERS on lib/cache-tags.ts |

---

## 8. TypeScript enforcement

```json
// tsconfig.json — non-negotiable
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true
  }
}
```

CI: `tsc --noEmit` on every PR.

ESLint:
- `@typescript-eslint/no-explicit-any`: error
- `@typescript-eslint/no-floating-promises`: error (server code)

---

## 9. Rust enforcement

```toml
# clippy.toml / lib.rs
# deny(unwrap_used) in non-test code
```

CI:
```bash
cargo clippy -- -D warnings
cargo test
```

---

## 10. Pre-commit stack (2026 standard)

```
husky pre-commit:
  1. tsc --noEmit
  2. lint-staged (eslint --fix, prettier)
  3. engineer-scan

husky pre-push:
  1. vitest run
  2. (optional) engineer-scan --strict
```

lint-staged scopes to changed files — fast feedback.

---

## 11. CI pipeline reference architecture

```
PR opened
  ├─ typecheck
  ├─ eslint --max-warnings=0
  ├─ engineer-scan --strict
  ├─ vitest
  ├─ playwright e2e smoke (5-15 flows)
  ├─ playwright axe (critical paths)
  ├─ supabase test db (pgTAP RLS)
  └─ gitleaks

merge to main
  └─ deploy preview → lighthouse / CWV check (optional)
```

Parallelize independent jobs. Target <10 min total.

---

## 12. Production observability enforcement

| Metric | Threshold | Tool |
|---|---|---|
| LCP | p75 ≤ 2.5s | CrUX / Vercel Analytics |
| INP | p75 ≤ 200ms | web-vitals RUM |
| Error rate | <0.1% on mutations | Sentry |
| Failed auth | spike alert | Supabase Auth logs |
| Webhook 5xx | 0 sustained | Stripe dashboard |

---

## Module map

| Domain | Enforcement doc section | Scanner flag |
|---|---|---|
| Design tokens | enforcement.md § ESLint + grep | `--design` |
| a11y | enforcement.md § Playwright axe | `test:a11y` |
| RLS | check-rls-migration.sh + pgTAP | `--backend` |
| Server Actions | grep auth | `--strict` |
| Webhooks | grep raw body | `--backend` |
| Secrets | gitleaks + scan | always |

---

## Canonical sources

- https://github.com/dequelabs/axe-core-npm/tree/develop/packages/playwright
- https://github.com/chandansamal/a11y-next-app
- https://makerkit.dev/blog/tutorials/secure-nextjs-server-actions
- https://makerkit.dev/blog/tutorials/supabase-rls-best-practices
- https://supabase.com/docs/guides/database/testing
- https://github.com/gitleaks/gitleaks
- https://nextjs.org/docs/app/building-your-application/configuring/eslint
