# engineer research report

**Date**: 2026-07-16
**Human docs**: [docs/README.md](../docs/README.md) · **Audit**: [gap-audit.md](gap-audit.md) · **Deepen**: [deep-2026-07.md](deep-2026-07.md) · **Python**: [python/](python/)

## Executive summary

engineer is a **router skill** composing specialist modules. Rules are grounded in
**2026 web research** (WCAG 2.2, DTCG tokens, Supabase/Next docs, PLG funnels,
Stripe webhooks, OTel, job runners), not a single-project aesthetic reference.

| Layer | Source | Role |
|---|---|---|
| Agent router | `SKILL.md` | Verbs, routing, flows, hard gates |
| Human docs | `docs/` | Install, verbs, CI setup, module map |
| Reference modules | `references/*.md` | Domain rules (agent, on demand) |
| Research | `research/*.md` | Provenance (via module footers only) |
| Enforcement | `scripts/`, `templates/` | Policy-as-code |
| Copy quality | unmachined | Anti-slop audits |
| Ship | gstack | qa, cso, ship |

Capability promotion: Engineer detects evidence-backed recurring workflows, chooses
the smallest durable owner, and invokes `skill-creator` only after a new or changed skill beats
project code, repository instructions, Engineer, and installed-skill reuse.

That ownership decision is replayable. A canonical receipt derives recurrence or
consequence qualification, complete owner comparison, router/evidence sufficiency, skill-creator and
evaluation coverage, destination authority, independent review, lifecycle ownership, and
new-skill non-duplication.

Captured-label forgery is closed: a captured ownership claim now replays exact signal,
catalog, authority, and canonical-decision review artifacts through confined hash-bound paths.

Executable mobile-web quality: the Playwright pack now runs a guarded iPhone lane
and a 320px compact lane that detect page overflow, missing device-width metadata, disabled zoom,
and maximum zoom below 200%, while keeping real-device limitations explicit.

MCP admission follows the latest stable 2025-11-25 contract: ordered OAuth/OIDC
discovery, Client ID Metadata security, verified PKCE S256, scope step-up, and mode-specific
elicitation controls are now replayable; experimental Tasks remain quarantined.

Expert pushback is a top-level operating principle. Engineer separates the
user's desired outcome from a proposed method, resists instructions to suppress evidence-backed
challenge, and continues safe work around the smallest supported alternative instead of stopping at
criticism.

It also adds goal-to-runtime system assurance: accepted product goals, roles, state transitions,
business invariants, and critical journeys map to focused frontend/backend tests, contract and
permission checks, browser journeys, failure recovery, correlated runtime signals, and explicit
residual risk. Universal "100% functional" claims are rejected unless the contract is closed and
finite.

Engineer includes a cross-surface visual-communication system. It chooses infographics by the
reader's question, treats blueprints and field notes as evidence-bearing editorial forms, and gives
X/blog visuals, YouTube thumbnails, logos, watermarks, GitHub previews, and channel banners distinct
composition, crop, accessibility, provenance, export, and measurement contracts.

Production completeness is the default: ambiguity cannot silently reduce scope, test
doubles stay confined to explicit/test contexts, and TODOs, fake success, skipped checks, dead UI,
hidden unfinished branches, or "for now" deferrals block completion in affected production scope.

Whole-company operating-system context is covered without duplicating the private strategy skill. Engineer can now
map executive and functional accountability, human-relations safeguards, governance, finance,
marketing, sales, security, legal operations, controls, evidence, exceptions, appeals, integration,
and assurance while reserving strategy, people decisions, capital allocation, and professional legal
or accounting judgment to accountable humans.

Two security boundary modules sit below the app layer. `infra-security.md`
owns cloud IAM least privilege, network exposure discipline, SSH/VPS hardening for
an RPC edge-node venture, OrbStack container hardening, production secrets stores, and backup/DR
security, scoped to the stack actually in use (K8s-at-scale and hyperscaler org policy stay
explicitly out of scope). `compliance-controls.md` maps SOC 2 / ISO 27001 / GDPR themes onto
existing modules and gates, classifies controls met-by-evidence / met-by-policy / gap into an
owned controls register, and treats retained receipts and audit events as compliance
evidence — while never claiming compliance status; certification and legal questions route to
company-operating-system governance and human counsel.

`long-horizon-agents.md` is distilled from the 12-item private
`agent-longevity-research` corpus: the empirically grounded session-degradation model (context
rot, lost-in-the-middle, multi-turn drift, self-conditioning, compaction loss), phase context
budgets and the fan-out-vs-single-thread boundary, the externalized-state spine contract
(conversation is cache, files are truth), compact/restart/handoff hygiene, ongoing/cron
fresh-context run patterns with snapshot + append-only journal state, and degradation detection
signals with a recovery protocol. Research notes: `long-horizon-agents-2026-07.md`.

Eval-harness live runner: a stdlib-only runner drives Claude Code
headless print mode against a curated `evals/live-smoke.json` subset, detects real routing
through the sealed `[routing-probe:alpha]` → activation-marker contract, grades assert/forbid
substrings, and compares a with-skill arm against a `--disable-slash-commands` baseline arm
with strict and content-only lift. Opt-in only (`run-evals.sh --live`); default CI stays
model-free with a shimmed-host fixture. First measured finding: advisory-form fix prompts get
correct root-cause behavior without a Skill-tool body load (tracked as a `known_gap` xfail),
while build-shaped prompts load the body and emit the sealed marker.

Token-economy optimization: the L1 description gains sibling negative triggers
(unmachined, gstack, vercel react-best-practices) inside the 1024-char budget, and
`enforcement.md` splits structure-only into setup/orientation plus an `enforcement-rules.md`
catalog with every rule preserved verbatim and inbound references re-pointed.

Ambient portfolio context: project detection reads workspace registry, global
agent policy, and the control plane's machine-readable policy and health snapshot (never
rescanning), resolves repo→venture through the declared mapping with "unknown — ask" fallback,
runs a cross-repo impact checklist, and escalates founder holds, disabled automation, and
unhealthy workspaces. Engineer loads portfolio facts; portfolio decisions stay with the private strategy skill.

Root cause is a diagnosis obligation for every fix: reproduce, name the violated
invariant, trace the causal chain to the first divergence, and repair there. Symptom patches
(retry masking a race, null guard hiding a broken invariant, widened timeout hiding an N+1) are
defects; symptom-level mitigations ship only declared, with owner, expiry, tracked follow-up,
and detection, and reports distinguish "mitigated" from "root-cause fixed."

Deep research was strengthened after a pinned, read-only comparison with
`Imbad0202/academic-research-skills`. It adds a research charter, claim-relative source fitness,
coverage and contradiction ledgers, time/version consistency, explicit degraded states, a research
integrity sweep, and calibration requirements before a model semantic reviewer becomes a hard gate.

Evidence-backed expert pushback is binding: Engineer challenges consequential flawed
premises, researches uncertain or drifting decisive claims, proposes the smallest better path, and
distinguishes user-owned tradeoffs from non-negotiable safety and authority gates.

Multi-turn completion paths are hardened: success requires observed evidence and state,
planned completion, fresh state-matching checkpoints, and exactly one final declared stop.

**2026-07-15 deepen**: browser QA lanes, parallel-safe Playwright, behavioral
design, product marketing, GTM engineering, product analytics/KPI, and
product-business engineering. engineer remains a standalone product-engineering skill.

## Documentation map

| Audience | Start here |
|---|---|
| Install & first prompt | [docs/getting-started.md](../docs/getting-started.md) |
| Verb reference | [docs/verbs.md](../docs/verbs.md) |
| CI / pre-commit | [docs/enforcement-setup.md](../docs/enforcement-setup.md) |
| Skill structure | [docs/architecture.md](../docs/architecture.md) |
| All modules | [docs/modules.md](../docs/modules.md) |
| Agent module index | [references/MANIFEST.md](../references/MANIFEST.md) |
| Coverage & roadmap | [gap-audit.md](gap-audit.md) |
| Multi-domain deepen | [deep-2026-07.md](deep-2026-07.md) |
| Skill authoring | [agent-skills-research.md](agent-skills-research.md) |

## Research corpora

| Corpus | Feeds |
|---|---|
| [deep-2026-07.md](deep-2026-07.md) | **All domains**: deepen + misses (start here for gaps) |
| [gap-audit.md](gap-audit.md) | Coverage matrix, P0-P2 roadmap |
| [oss-safe-application-2026-07.md](oss-safe-application-2026-07.md) | Safe automatic OSS local remediation and policy-decision boundary |
| [capability-promotion-2026-07.md](capability-promotion-2026-07.md) | Evidence-backed reuse, extension, project ownership, and new-skill promotion decisions |
| [agent-trajectory-evals-2026-07.md](agent-trajectory-evals-2026-07.md) | Multi-turn path and outcome evaluation, checkpoint freshness, and trace limits |
| [company-leadership-operations-2026-07.md](company-leadership-operations-2026-07.md) | Whole-company leadership, functional interfaces, people systems, governance, controls, and professional boundaries |
| [academic-research-skills-review-2026-07.md](academic-research-skills-review-2026-07.md) | Pinned supply-chain comparison and adopted research-integrity patterns |
| [mobile-web-quality-2026-07.md](mobile-web-quality-2026-07.md) | 320px reflow, viewport zoom policy, Playwright emulation, and real-device limits |
| [design-research.md](design-research.md) | Design modules |
| [frontend-research.md](frontend-research.md) | Frontend modules |
| [backend-research.md](backend-research.md) | Backend modules |
| [security-research.md](security-research.md) | App security (full threat model, CSP, actions, RLS) |
| [enforcement-research.md](enforcement-research.md) | Enforcement |
| [coding-research.md](coding-research.md) | Coding & architecture |
| [growth-research.md](growth-research.md) | Growth & conversion |
| [ai-agents-research.md](ai-agents-research.md) | Agent prompting |
| [agent-skills-research.md](agent-skills-research.md) | Skill authoring |
| [refactoring-research.md](refactoring-research.md) | Fowler + progressive disclosure |
| [agent-memory-context-governance-2026-07.md](agent-memory-context-governance-2026-07.md) | Durable memory provenance, isolation, retrieval, and lifecycle governance |
| [llmquota-ring-boundary-2026-07.md](llmquota-ring-boundary-2026-07.md) | Quota/ring ownership and safe cross-CLI notification composition |
| [mcp-security-2026-07.md](mcp-security-2026-07.md) | MCP authorization, capabilities, tool schemas, and runtime calls |
| [agent-completion-evidence-2026-07.md](agent-completion-evidence-2026-07.md) | Contract-defined acceptance oracles and hash-bound completion proof |
| [optimization-evidence-2026-07.md](optimization-evidence-2026-07.md) | Captured paired trials, holdout isolation, blinded grading, and optimization promotion proof |
| [optimization-provenance-2026-07.md](optimization-provenance-2026-07.md) | Signed optimization evidence, trusted workflow identity, and offline verification policy |
| [optimization-attribution-2026-07.md](optimization-attribution-2026-07.md) | Exact variant bundles and deterministic one-variable attribution |
| [optimization-runtime-binding-2026-07.md](optimization-runtime-binding-2026-07.md) | Captured trial identity binding to exact variant layers |
| [browser-multilane-enforcement-2026-07.md](browser-multilane-enforcement-2026-07.md) | Fail-closed authenticated read/write lane execution |
| [browser-lane-evidence-2026-07.md](browser-lane-evidence-2026-07.md) | Aggregate identity, ownership, overlap, concurrency, artifact, and cleanup proof |
| [web-discovery-2026-07.md](web-discovery-2026-07.md) | SEO, SEA, AI answers, crawler standards, llms.txt status, consent, and measurement |
| [hermes-agent-2026-07.md](hermes-agent-2026-07.md) | Hermes Agent architecture, tools, security, memory, browser, cron, profiles, and self-improvement |
| [coding-agent-hosts-2026-07.md](coding-agent-hosts-2026-07.md) | Codex, Claude Code, Hermes capability adaptation and cross-host evidence |
| [external-agent-methods-2026-07.md](external-agent-methods-2026-07.md) | autoresearch, gstack, and Superpowers capability comparison and integration boundary |
| [agent-skill-ecosystem-2026-07.md](agent-skill-ecosystem-2026-07.md) | GitHub skill ecosystem trust classes, specialist inputs, and Engineer composition decisions |
| [commercial-product-surfaces-2026-07.md](commercial-product-surfaces-2026-07.md) | Landing, sales, portfolio, dashboard, product, RevOps, and company-policy implementation evidence |
| [deep-research-evidence-2026-07.md](deep-research-evidence-2026-07.md) | Claim-level provenance, temporal integrity, citation limits, and report publication gates |
| [clean-engineering-2026-07.md](clean-engineering-2026-07.md) | Proportional architecture, SOLID boundaries, reversibility, and anti-overengineering gates |
| [csp-reporting-2026-07.md](csp-reporting-2026-07.md) | CSP Level 3 reporting, privacy-minimized ingestion, and promotion evidence |
| [oss-maintainer-2026-07.md](oss-maintainer-2026-07.md) | Proportional public OSS governance, security, contribution, release and sustainability operations |
| [portage-boundary-2026-07.md](portage-boundary-2026-07.md) | Portage portable handoff ownership and trust boundary |

## Capability summary

- Security, billing, deploy-ops, observability, SEO, email, onboarding
- i18n, storage, backend testing, flags, compliance, monorepo, storybook
- SKILL dedup, MANIFEST, skill-authoring, evals, human docs/ hub
- Slash commands, workflows, loops
- OSS prep, brand kit, validate CI
- Refactor verb, progressive-disclosure SKILL, research deepen + gap rewrite

**Next P0 candidates**: background-jobs module, backend-multitenant, OTel template,
Playwright template, rate-limit scan rules. **Deferred**: pgvector/AI, Expo, gRPC.

---

## Prior notes (stack + backend)

See sections below for Next.js 16 cache, Supabase SSR, shadcn, and agent skill
landscape research from initial build.

Differentiator vs existing skills: engineer adds **design system + a11y + patterns**
as first-class modules alongside TypeScript/Rust/API flows.

---

## 1. Design & frontend (web research)

**Design corpus**: `research/design-research.md`
**Frontend corpus**: `research/frontend-research.md`
**Backend corpus**: `research/backend-research.md`

Key 2026 standards encoded in engineer:
- Three-tier design tokens (primitive → semantic → component)
- WCAG 2.2 AA at component source (not overlay widgets)
- 8pt grid + 12-column layout + mobile-first breakpoints
- Form UX: labels above, on-blur validation, field-level errors
- Dashboard UX: F-pattern, one task per screen, defaults not empty
- shadcn: wrapper pattern, OKLCH tokens, `@theme inline`
- RSC default; client islands at leaves
- Core Web Vitals: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 (field data)
- State: URL → Server/RSC → Query → Zustand (UI only)
- Granular Suspense; skeletons with fixed dimensions
- Testing: Vitest + RTL + Playwright (5-15 E2E flows)
- RLS on all public tables; `(select auth.uid())` in policies
- Server Actions = public endpoints; auth + Zod + rate limit
- `updateTag` in Actions; `revalidateTag` in Route Handlers
- Webhook signature verify + idempotency on event ID

---

## 2. Next.js 16 / App Router (docs + GitHub)

**Sources**: nextjs.org/docs (cacheComponents, caching), Vercel Academy,
GitHub vercel/next.js#89375, noqta.tn cache guide

### Key shifts (2026)

- **Dynamic by default**; caching is opt-in via `'use cache'`
- **PPR is default** with `cacheComponents: true`: static shell + streamed dynamic holes
- **`use cache` placement**: on data functions / leaf components, NOT page orchestrators
- **Invalidation split**:
  - `updateTag()`: read-your-own-writes (Server Actions)
  - `revalidateTag(tag, profile)`: stale-while-revalidate background refresh
- **Never** `cookies()`/`headers()` inside `use cache` scope
- **Suspense** for user-specific dynamic content; don't wrap entire `<body>`

### Encode in engineer

Add to `data-layer.md` and `stack-rules.md`:
- Explicit cacheLife on every `use cache`
- Cache tag registry pattern for growing apps
- `connection()` only for whole-page dynamic; prefer Suspense + cache elsewhere

---

## 3. Tailwind v4 / design tokens (docs)

**Sources**: tailwindcss.com/docs/theme, llmbestpractices.com/tailwind-theme,
DesignDev.io token system, DEV raxxostudios

### Two-layer token model (recommended)

```css
:root {
  --accent: #c5f23f;
  --bg: #08090a;
}

@theme inline {
  --color-accent: var(--accent);
  --color-bg: var(--bg);
}
```

- **Static tokens** in `@theme` (spacing, fonts, shadows)
- **Themeable tokens** via `@theme inline` + `:root` / `.dark` overrides
- **Namespace prefixes are load-bearing**: `--color-*`, `--radius-*`, `--font-*`
- **OKLCH** for new projects; `color-mix()` for derived tints is also valid
- **CI grep**: fail build on `@theme` vars missing known namespace prefix

### shadcn + Tailwind v4

- Theme at token layer in `globals.css`, not in component files
- Wrapper pattern for structural changes (never edit `components/ui/*`)
- Product abstractions: `AppButton`, `AppDialog` wrapping shadcn primitives
- CVA for variants; `cn()` for merge
- OKLCH cssVars in shadcn init is 2026 best practice (llmbestpractices, eastondev)

---

## 4. Supabase + Next.js (docs + GitHub)

**Sources**: supabase.com/docs (SSR client), supabase/ssr, supabase/server,
SecureStartKit 2026 guide, DEV Community RLS guide

### Auth architecture (2026)

1. **Middleware**: refresh tokens; MUST implement `getAll` + `setAll`
2. **Middleware protection**: prefer `getClaims()` (JWT verify locally)
3. **Server Components/Actions**: use `getUser()` (DB-validated)
4. **Never** trust `getSession()` alone on server
5. **Never** expose service role; admin client server-only with comments

### RLS

- Enable on every `public` table, with no exceptions
- Separate INSERT/SELECT/UPDATE/DELETE policies
- Test with `SET ROLE` in SQL before deploy
- Server client resolves `auth.uid()` via cookies; anon client will not

### New note: `@supabase/server` (2026)

Composable with `@supabase/ssr`:
- ssr = cookie lifecycle
- server = JWT verify, RLS-scoped context client, admin client

engineer should mention this for advanced setups but default to `@supabase/ssr`.

---

## 5. Conversion / SaaS landing (web research)

**Sources**: vezadigital.com 2026 patterns, saasframe.io trends, saasdesign.io

### High-converting structure (2026)

1. **One objective per page**: remove nav on pure landing when possible
2. **5th-7th grade reading level**: outcome language, not feature dumps
3. **Product-first hero**: real screenshots/terminal > abstract 3D
4. **Bento grids**: modular feature scan for multi-capability products
5. **Sticky primary CTA**: after scroll past hero
6. **Minimal signup friction**: defer profile fields post-auth
7. **Social proof with attribution**: name, role, company
8. **Typography personality**: neutral-only type is declining; contrast pairs OK

### Config-driven marketing patterns

- Central `site.ts` for copy/CTAs/links
- `lastUpdated` for freshness signals (sitemap, JSON-LD)
- Placeholder metrics with distinct styling, never invented
- Featured pricing tier with clear visual hierarchy

---

## 6. Existing agent skills landscape (GitHub)

| Repo | Strength | Gap engineer fills |
|---|---|---|
| vercel-labs/agent-skills | React perf (40+ rules) | No design system, a11y, conversion |
| jeffallan/claude-skills/nextjs-developer | App Router modules | Generic UI doctrine |
| enesdmc0/ai-skills | Supabase + Next auto-trigger | No design/accessibility modules |
| sateeshs/cc-nextjs (SSD) | Drizzle + shadcn scaffolding | No design patterns |
| Nembie/claude-code-skills | Route generators, reviewers | No WCAG/pattern encoding |
| unmachined (local) | Anti-slop copy + design tells | Does not build; audits |
| private strategy skill (local) | Business strategy router | Not engineering |

**engineer positioning**: Fullstack builder with **web-researched design system +
a11y + patterns** + TypeScript/Rust/API flows, composing unmachined + vercel
react-best-practices + gstack.

---

## 7. Module map

| Module | Purpose |
|---|---|
| `backend-security.md` | CSP, headers, OWASP hardening |
| `billing-stripe.md` | Checkout, Portal, entitlements |
| `deploy-ops.md` | Vercel, envs, migration deploy |
| `observability.md` | Logs, Sentry, tracing |
| `seo-metadata.md` | Technical SEO |
| `email-notifications.md` | Resend, lifecycle email |
| `product-onboarding.md` | Activation UI patterns |
| `ai-agents.md` | Prompting, context stack |
| `coding-principles.md` | SOLID, craft, review, Rule of Three |
| `system-architecture.md` | Monolith, bounded contexts, reliability |
| `growth-funnels.md` | PLG, activation, retention, PQL |
| `conversion-ui.md` | Landing layout, CTAs (router) |
| `enforcement.md` | CI, pre-commit, scanners, maturity model |
| `scripts/engineer-scan.sh` | Policy grep (colors, secrets, auth) |
| `scripts/check-rls-migration.sh` | RLS migration gate |
| `templates/github/*` | CI workflow + PR template |

| Module | Purpose |
|---|---|
| `design-system.md` | Tokens, color, type, spacing, motion |
| `design-accessibility.md` | WCAG 2.2 AA |
| `design-patterns.md` | Forms, dashboards, responsive |
| `frontend.md` | RSC, components, forms (router) |
| `frontend-performance.md` | CWV, images, fonts, bundle |
| `frontend-state.md` | State decision tree |
| `frontend-streaming.md` | Suspense, loading, errors |
| `frontend-testing.md` | Vitest, RTL, Playwright |
| `backend-supabase.md` | Backend router |
| `backend-auth.md` | SSR auth, sessions |
| `backend-database.md` | Migrations, RLS |
| `backend-api.md` | Actions, Route Handlers |
| `backend-webhooks.md` | Stripe, idempotency |
| `data-layer.md` | Cache, queries, realtime |
| `typescript.md` / `rust.md` | Language patterns |
| `api-data-flows.md` | Cross-service architecture |
| `stack-rules.md` | Next/Tailwind/shadcn implementation |

### Optional future

- `scripts/scan_design.py`: grep token/a11y slop scanner
- Visual regression in CI (Storybook/Chromatic)

---

## Canonical sources

See `research/design-research.md` for full design source list.

### Stack & backend
- https://nextjs.org/docs/app/api-reference/config/next-config-js/cacheComponents
- https://supabase.com/docs/guides/auth/server-side/creating-a-client
- https://tailwindcss.com/docs/theme
- https://github.com/vercel-labs/agent-skills
- https://ui.shadcn.com/docs/theming
- Local: companion skill `unmachined` → `references/stack-rules.md`
