# Code quality: ship gates, enforcement, review

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Full enforcement playbook: **`enforcement.md`**
Scanner: **`scripts/engineer-scan.sh`**

## Contents
- [Enforcement tiers](#enforcement-tiers)
- [Pre-ship checklist](#pre-ship-checklist)
- [Automated gates](#automated-gates)
- [TypeScript standards](#typescript-standards)
- [Error handling](#error-handling)
- [Testing guidance](#testing-guidance)
- [Review rubric](#review-rubric)
- [Anti-patterns](#anti-patterns)

## Enforcement tiers

| Tier | Mechanism | When |
|---|---|---|
| **0 Process** | PR template, CODEOWNERS, `engineer audit` | Every PR |
| **1 Local** | husky, lint-staged, `engineer-scan` | Pre-commit |
| **2 CI** | tsc, lint `--max-warnings=0`, tests, axe, pgTAP | Every push/PR |
| **3 Prod** | Sentry, CrUX, Stripe webhook alerts | Post-deploy |

Copy templates from `templates/github/`. Target **L2** before launch, **L3** before payments.

## Pre-ship checklist

Human verification - automate everything below that has a script:

```
Ship gate:
- [ ] npm run typecheck && npm run lint:ci && npm run engineer:scan -- --strict
- [ ] Types compile; no unjustified `any`
- [ ] Design: semantic tokens; 8pt spacing; 16px body min
- [ ] a11y: WCAG 2.2 AA contrast, focus visible, 44px targets (house default; AA floor 24px), labels on inputs
- [ ] Forms: on-blur validation, errors below field, multi-signal errors
- [ ] Zod validation on all external inputs
- [ ] Auth checked on mutations (getUser)
- [ ] RLS policies for new/changed public tables (check-rls-migration.sh)
- [ ] Loading, error, empty states implemented
- [ ] Responsive: 320, 375, 768 verified
- [ ] No secrets in client bundle
- [ ] No edits inside components/ui/* (use wrappers)
- [ ] .env.example updated for new env vars
- [ ] Migrations applied; types regenerated
- [ ] Rate limit on sensitive new actions (auth, billing, delete)
```

For full browser QA: gstack `/qa`.
For security-sensitive surfaces: gstack `/cso`.
For deploy: gstack `/ship`.

## Automated gates

### Minimum package.json scripts

```json
{
 "scripts": {
 "typecheck": "tsc --noEmit",
 "lint:ci": "eslint . --max-warnings=0",
 "engineer:scan": "bash scripts/engineer-scan.sh",
 "test:unit": "vitest run",
 "test:e2e": "playwright test",
 "test:a11y": "playwright test e2e/a11y"
 }
}
```

Copy `scripts/engineer-scan.sh` and `scripts/check-rls-migration.sh` from engineer
into project `scripts/`.

### What each gate catches

| Gate | Blocks |
|---|---|
| `typecheck` | Type errors, unsafe null access |
| `lint:ci` | a11y JSX, unused imports, `any` |
| `engineer-scan` | Hardcoded colors, secrets, updateTag in routes |
| `engineer-scan --strict` | Client layouts, action auth, localStorage JWT |
| `check-rls-migration.sh` | Tables without RLS enable |
| `test:a11y` | WCAG violations on critical paths |
| `supabase test db` | RLS policy matrix failures |

## TypeScript standards

- `strict: true` - never weaken for convenience
- `noUncheckedIndexedAccess: true` when project allows
- `interface` for object shapes; `type` for unions/intersections
- Prefer `unknown` over `any`; narrow with Zod or type guards
- Discriminated unions for complex state machines
- `const` assertions for literal config objects
- No `@ts-ignore` - fix or `@ts-expect-error` with reason

**Enforce**: `tsc --noEmit` in pre-commit + CI; ESLint `@typescript-eslint/no-explicit-any: error`.

Import order:
1. External packages
2. Internal aliases (`@/`)
3. Relative imports
4. Types (if separate)

## Error handling

Pattern for Server Actions:

```typescript
export async function createProject(input: unknown) {
 const parsed = projectSchema.safeParse(input);
 if (!parsed.success) {
 return { ok: false as const, error: "Invalid input" };
 }

 try {
 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { ok: false as const, error: "Unauthorized" };

 const { data, error } = await supabase
 .from("projects")
 .insert({ ...parsed.data, user_id: user.id })
 .select()
 .single();

 if (error) throw error;
 updateTag("projects");
 return { ok: true as const, data };
 } catch (e) {
 console.error("createProject failed", e);
 return { ok: false as const, error: "Could not create project" };
 }
}
```

Rules:
- User-facing errors: helpful, non-technical
- Log details server-side; never leak stack traces to client
- Early returns over deep nesting
- Typed result unions (`{ ok: true, data } | { ok: false, error }`)

## Testing guidance

| Layer | Tool | Enforce in CI |
|---|---|---|
| Schema/logic | Vitest | `test:unit` on PR |
| Server Actions | Vitest + mock Supabase | Auth gate tests |
| Components | RTL | Form validation tests |
| E2E | Playwright | 5-15 smoke flows |
| a11y | @axe-core/playwright | `test:a11y` on PR |
| RLS | pgTAP | `supabase test db` |

Do not add trivial tests that assert implementation details.
Do not skip auth/RLS testing on multi-tenant features.

## Review rubric

Score 0-100 when running `engineer audit`:

| Dimension | Weight | Checks |
|---|---|---|
| Correctness | 25% | Logic, edge cases, auth, RLS |
| Stack fit | 20% | RSC/client boundaries, Tailwind v4, shadcn |
| Taste | 15% | Token usage, hierarchy, restraint |
| Conversion | 15% | Clear primary action, friction, trust |
| Maintainability | 15% | File size, naming, feature boundaries |
| Performance | 10% | Parallel fetch, bundle, images |
| **Enforcement** | +bonus | Automated gates present and passing |

≥80 = ship-ready · 60-79 = fix before merge · <60 = rework

Report: quote → rule → fix → **enforcement recommendation**.
Severity: critical / suggestion / nice-to-have. Tag each finding with its confidence
(`observed` from code or a run, `inferred` from patterns); never state an inference as observed.

### Severity vocabularies (one mapping)

Every Engineer surface keeps its native labels; this table is the exchange rate when findings
cross surfaces or land in one report. The canonical machine scale is the security findings
receipt (`low` / `medium` / `high` / `critical`, plus `confidence`).

| Surface | Native labels | Canonical |
|---|---|---|
| `engineer audit` rubric | critical / suggestion / nice-to-have | high–critical / medium / low |
| `engineer qa` (`browser-qa.md`) | Critical / High / Medium / Low | same names |
| Security findings receipt | confirmed-only severity, overall ≤ impact | canonical |
| `check-oss-leaks.sh` | CRITICAL / MAJOR / NOTE | critical / high / low |
| `engineer-scan.sh` | error / warn | high / medium |
| `scan-false-done.sh` | BLOCK / warn | high / medium |
| Admission receipts | reject / quarantine / trust | decision, not severity |
| `compliance-controls.md` | met-by-evidence / met-by-policy / gap | status, not severity |

## Anti-patterns

- Checklist-only gates with no CI automation
- `eslint` without `--max-warnings=0` in CI
- Skipping engineer-scan "because small PR"
- RLS deferred to "next sprint"
- a11y overlay widget instead of eslint + axe
- `any` to silence errors
- Swallowed catch blocks
- Console.log in production paths
- Tests that mock everything and assert nothing
- Shipping without empty states

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
