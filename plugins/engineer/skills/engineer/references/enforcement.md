# Enforcement: how to make engineer rules stick

**Last verified**: 2026-07-16 · **Review cadence**: 3 months
**Related**: `enforcement-rules.md` (the exact rule catalog: scanner rules, lint configs, grep gates, rule→enforcement maps)

Rules without enforcement decay. Use **four tiers** - each catches what the
previous tier misses.

```
Tier 0 Agent/human engineer audit · PR checklist · CODEOWNERS
Tier 1 Local pre-commit · lint-staged · engineer-scan
Tier 2 CI GitHub Actions · --max-warnings=0 · E2E
Tier 3 Production RUM · error tracking · security monitoring
```

Full research: `research/enforcement-research.md`
Scanner: `scripts/engineer-scan.sh`
Rule catalog (rate-limit rules, scan categories, ESLint baseline, a11y/auth/RLS gates,
rule→enforcement maps, secret-scan patterns): **`enforcement-rules.md`**

## Contents
- [Tier 0 - Process gates (always)](#tier-0---process-gates-always)
- [engineer ship gate](#engineer-ship-gate)
- [Tier 1 - Local enforcement](#tier-1---local-enforcement)
- [Tier 2 - CI enforcement](#tier-2---ci-enforcement)
- [Tier 3 - Production enforcement](#tier-3---production-enforcement)
- [Enforcement maturity model](#enforcement-maturity-model)
- [Anti-patterns](#anti-patterns)

## Tier 0 - Process gates (always)

### PR template (`.github/pull_request_template.md`)

```markdown
## engineer ship gate
- [ ] Zod on new external inputs
- [ ] Auth on new mutations (`getUser()`)
- [ ] RLS migration if schema changed
- [ ] Loading / empty / error states
- [ ] Semantic tokens (no hardcoded colors)
- [ ] a11y: labels, focus, contrast checked
- [ ] Types regenerated if migration applied
```

### CODEOWNERS (require review on sensitive paths)

```
# .github/CODEOWNERS
supabase/migrations/ @your-team/backend
lib/supabase/ @your-team/backend
app/api/webhooks/ @your-team/backend
components/ui/ @your-team/design-system
.env* @your-team/infra
```

### Branch protection

- Require CI pass before merge
- Require 1+ review on `main`
- Block force-push to `main`
- Require CODEOWNERS approval where configured

### Agent enforcement

When building with engineer, run mentally (or explicitly):

```
engineer audit <target> → score against module rubrics before merge
engineer fix <target> → repair flagged issues
```

---

## Tier 1 - Local enforcement

### Package scripts

```json
{
 "scripts": {
 "engineer:scan": "bash path/to/engineer/scripts/engineer-scan.sh",
 "engineer:scan:strict": "bash path/to/engineer/scripts/engineer-scan.sh --strict",
 "lint:ci": "eslint . --max-warnings=0",
 "typecheck": "tsc --noEmit",
 "test:unit": "vitest run",
 "test:e2e": "playwright test",
 "test:a11y": "playwright test e2e/a11y",
 "test:rls": "supabase test db",
 "prepush": "npm run typecheck && npm run lint:ci && npm run engineer:scan"
 }
}
```

Copy-paste starter: `templates/package-scripts.snippet.json`

### Husky + lint-staged

```bash
npm install --save-dev --save-exact husky@9.1.7 lint-staged@17.0.8
npm exec --offline -- husky init
```

```json
// package.json
{
 "lint-staged": {
 "*.{ts,tsx}": [
 "eslint --fix --max-warnings=0",
 "prettier --write"
 ],
 "supabase/migrations/*.sql": [
 "bash scripts/check-rls-migration.sh"
 ]
 }
}
```

```bash
# .husky/pre-commit
npm run typecheck
npm exec --offline -- lint-staged
npm run engineer:scan
```

```bash
# .husky/pre-push (heavier checks)
npm run test:unit
```

### engineer-scan (local policy grep)

Runs from repo root; copy `scripts/engineer-scan.sh` into project or symlink from
engineer install. Flag-by-flag rule categories, rate-limit surfaces, and exemption
comments: `enforcement-rules.md`.

---

## Tier 2 - CI enforcement

### Minimum CI pipeline (every PR)

Copy **`templates/github/engineer-gates.yml`** to `.github/workflows/`. It ships
SHA-pinned actions (Node 24) and these jobs - do not hand-write a lookalike:

```yaml
jobs:
 static:   # npm ci → typecheck → lint:ci (zero warnings) → engineer-scan --strict
 unit:     # test:unit (needs static)
 e2e:          # playwright chromium smoke (needs static)
 a11y:         # playwright a11y suite (needs static)
 secrets:      # layered secret scan (see below)
 supply-chain: # frozen-lockfile + ignore-scripts + provenance + lifecycle allowlist
```

RLS pgTAP job (commented in the template), secret-scan patterns, a11y axe spec, and the
Server Action auth grep for this pipeline: `enforcement-rules.md`.

### Supply-chain job (2025-2026 attack class)

- Install with a **frozen lockfile** and `--ignore-scripts` (pnpm `onlyBuiltDependencies` /
  Bun `trustedDependencies` equivalents); fail on any lifecycle script not on a committed
  allowlist.
- Provenance-verify step: `npm audit signatures` / `gh attestation verify`; report coverage and
  flag an unexpected build path or a newly-absent attestation on a critical dep. Do not fail on
  mere absence.
- SHA-pin every third-party Action to a full 40-char commit (not a mutable tag); forbid
  `pull_request_target`/`workflow_run` workflows that check out fork code or reference repository
  secrets (`scan-doc-supply-chain.py` rules `privileged-trigger-fork-checkout` and
  `privileged-trigger-secrets`; `GITHUB_TOKEN`, bounded by `permissions:`, is exempt). Move secret
  use to a separate approval-gated job. Each YAML fence in docs is scanned as its own workflow.
- Dependency hygiene rationale and package-manager defaults: `backend-security.md`.

### Layer the secrets job (a clean scan does not clear a public push)

Pre-commit (`check-oss-leaks.sh` SECRET class / gitleaks, network-free) -> CI (gitleaks in the
template's `secrets` job; TruffleHog `--only-verified` as an optional second scanner that fails
on live secrets) -> server-side (GitHub push protection). A clean SECRET
scan does **not** clear a public push: the anchor's base64 URL is a *dropper indicator, not a
credential* - run the DROPPER/ENVB64/INVISIBLE_UNICODE pass (`check-oss-leaks.sh`) too.

### Malware method-families -> the four tiers

| Tier | Control | Cross-link |
|---|---|---|
| Tier 1 (commit) | `check-oss-leaks.sh` regex (encoder+sink, ENVB64, invisible-unicode) | `malware-detection.md` |
| Tier 2 (CI) | Semgrep/CodeQL decode-source -> exec-sink taint (cross-file) + **gated** entropy | `malware-detection.md` |
| Admission | GuardDog + sandbox detonation with egress observation | `skill-supply-chain.md` |

Tier 1 is same-file only; the cross-file config<->`.env` split is Tier 2's job (taint). Entropy
is a gated triage signal - path-excluded, capability-correlated, allowlisted - never a gate alone.

### Bundle budget (optional)

```yaml
 - run: ANALYZE=true npm run build
 - name: Check bundle size
 run: npx size-limit
```

---

## Tier 3 - Production enforcement

| Signal | Tool | Action |
|---|---|---|
| CWV regression | Vercel Analytics / CrUX | Alert on LCP/INP/CLS threshold breach |
| Runtime errors | Sentry / Axiom | Pager on mutation failure spike |
| Auth anomalies | Supabase Auth logs | Alert on failed login burst |
| RLS bypass attempt | Postgres logs | Audit service_role usage |
| Webhook failures | Stripe dashboard | Alert on repeated 500s |

---

## Enforcement maturity model

| Level | Characteristics |
|---|---|
| **L0 Ad hoc** | Checklists only; engineer audit manual |
| **L1 Local** | husky + lint-staged + engineer-scan |
| **L2 CI** | PR gates: tsc, lint, scan, unit, e2e smoke |
| **L3 Hardened** | + a11y axe, pgTAP RLS, secret scan, bundle budget |
| **L4 Observable** | + prod monitoring, CWV alerts, Sentry |

Greenfield SaaS target: **L2 minimum**, **L3 before payments**.

---

## Anti-patterns

- Checklist in PR template nobody reads - automate what you can
- a11y overlay widget instead of eslint + axe
- CI that doesn't fail on warnings (`eslint` without `--max-warnings=0`)
- RLS "we'll add later" - block merge on missing policies
- Skipping scan because "it's a small PR"
- Enforcement only in CI (no local pre-commit) - slow feedback loop

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
