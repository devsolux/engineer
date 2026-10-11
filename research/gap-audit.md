# engineer gap audit

**Date**: 2026-08-23
**Purpose**: Coverage vs a production fullstack SaaS OS - filled, thin, deferred, and missed.
**Companion**: [deep-2026-07.md](deep-2026-07.md) · [report.md](report.md) · [python/](python/)
**Loop/AI eng synthesis**: distilled into `references/workflows.md`, `references/agentic-engineering.md`, and `external-agent-methods-2026-07.md` (source pack was a private workspace repo, not vendored)
**Partner reference**: gstack to `references/composition.md`
**Deep research**: Weizhena-style pipeline in `references/deep-research.md`

Gaps: strong · thin (exists but incomplete) · deferred · missing

---

## Executive snapshot (current)

Live inventory: **51** slash commands, **208** eval scenarios, **109**
reference modules + MANIFEST, **100** scripts. SKILL.md is a router (under 500 lines).
`design-taste.md` is the aesthetic contract; `--design` scan flags measured 2026 tells.
Skill-eval hash-chain rebind is a local health fixture, not only CI.

2026-08 refresh: Next 16 + `proxy.ts` + Cache Components is the greenfield default;
MCP pins **2026-07-28**; Stripe default is Checkout Sessions; Agent Skills spec
fields `license` / description limits are enforced; operator X-article runbooks
are gated out of this repo.

| Area | Status | Notes |
|---|---|---|
| **Skill router / progressive disclosure** | strong | L2 restored; design-motion and long-horizon are at-need, not default verb loads |
| **Stack pins** | strong | COMPAT 2026-08-19: Next 16.x LTS, React 19.2, Tailwind v4 `@source`, `proxy.ts` |
| **MCP authorization and runtime evidence** | strong | Spec pin 2026-07-28; OAuth/OIDC, PKCE S256, streamless elicitation, captured-call validator; Tasks remain an opt-in extension |
| **Outer-loop / risk gates / maker-checker** | strong | `workflows.md` + `/engineer-loop-agent` |
| **AI boundary / security / evals / pgvector** | strong | ai-* + `backend-pgvector` |
| **FTS / admin / metered / flags / motion** | strong | modules shipped 2026-07-14 cycles |
| **Onboarding empty states + checklist** | strong | `product-onboarding.md` deepened |
| **Eval specification CI** | strong | validate.yml + 208 structurally checked scenarios |
| **Cross-domain expert-depth contract** | strong | project truth, governing sources, characteristic failures, native artifacts, same-layer proof, and explicit unknowns |
| **Goal-to-runtime system assurance** | strong | product truth model, business-rule and journey traceability, layered full-stack tests, first-divergence debugging, production evidence, and residual-risk boundary |
| **Visual communication and distribution assets** | strong | question-based infographic taxonomy; truthful blueprints/field notes; X/blog, thumbnail, identity, watermark, GitHub and banner contracts; crop, accessibility, provenance and measurement gates |
| **Implementation completeness** | strong | production-by-default scope, ambiguity gates, anti-mock/placeholder/defer sweep, real-boundary evidence, and honest partial/blocked states |
| **Root-cause fix engineering** | strong | fix-site diagnosis contract, symptom-patch prohibition, declared-mitigation protocol, fix-time architecture gates, and mitigated-vs-fixed completion language |
| **Portfolio/workspace context** | strong | declared workspace-truth sources, machine-readable repo→venture resolution, snapshot-not-rescan health, cross-repo impact checklist, hold escalation, facts-not-decisions boundary |
| **Deep-research claim evidence** | strong | claim graph, exact topic set/cutoff, source consistency, and hash-bound independent claim-support review with explicit semantic limits |
| **Research framing and integrity** | strong | Phase 0 charter, claim-relative evidence fitness, coverage/contradiction ledger, time/version checks, degraded states, failure sweep, and reviewer-calibration boundary |
| **Behavioral skill evidence** | strong | captured hash-bound runs, outcome/trajectory graders, calibration and promotion gates |
| **Evidence path identity** | strong | one lexical contract rejects traversal, escape, and final or parent symlinks inside evidence roots; every evidence JSON/JSONL CLI reader preserves and rejects a final supplied symlink before resolution |
| **Evidence publication identity** | strong | immutable receipts use exclusive non-following creation; MCP packages require a new directory; telemetry serializes validated identity-checked appends; regenerable reports remain distinct |
| **Provider-executed private baseline corpus** | capture-ready | sealed Codex/Claude adapters, transaction-marked batch preparation and local telemetry exist; genuine private runs remain manual and out of default CI |
| **Implicit skill activation** | strong | sealed exactly-once activation marker plus a live local runner (`run-live-evals.py`) that drives `claude -p` with probe-token activation detection and a skills-disabled baseline arm with measured lift; provider-executed cross-host captures remain manual |
| **Anti-overengineering / proportional architecture** | strong | schema-v2 plan complexity receipt binds present evidence, simplest design, abstractions/components, SOLID pressure, reversibility and rejected options |
| **Verified commit and deployment provenance** | strong | local-vs-GitHub signature semantics, co-author limits, native signed-commit ruleset, exact-SHA fail-closed deploy gate |
| **CSP reporting and promotion** | strong | modern/legacy bounded ingest, privacy minimization, poison resistance, Report-Only-to-enforce decision gate |
| **OSS maintainer operations** | strong | automatic public-repo mode, proportional audit, documented-ecosystem dependency updates with ambiguity evidence, independently replayed schema-v2 receipt, community/governance/security/release/sustainability contract |
| **Engineer evaluation telemetry** | strong | opt-in local metadata-only ledger, validator, summary, privacy gates, optional OTel boundary |
| **Skill and executable-guidance supply chain** | strong | semantic admission, source-class routing, catalog non-transitivity, and syntax-aware docs/workflow gate |
| **Capability-to-skill promotion** | strong | automatic detection plus a replayable ownership receipt and captured signal/catalog/authority/decision-review bindings covering collision, lifecycle, behavioral evidence, install, and retirement |
| **Third-party skill trust receipts** | strong | full tree/provenance/behavior/reviewer decision validator and adversarial fixtures |
| **Multi-agent runtime governance** | strong | contract plus captured-run proof for delegation, lanes, budgets, joins, traces, cancellation, synthesis |
| **Rate-limit template** | strong | `templates/lib/rate-limit.ts` + scan |
| **Portage handoff recipe** | strong | `composition.md` |
| **Trajectory / multi-turn evals** | strong | contract-bound ordered state machine covers observations, evidence, state, planned completion, fresh checkpoints, stop semantics, tool/security policy, and direct input identity; hosted trace exploration remains optional |
| **Acceptance completion proof** | strong | contract-defined JSON oracles, hash-bound captured evidence, exact command coverage, and independent completion review |
| **Prompt/loop optimization proof** | strong | exact captured-trial derivation, paired seeds, counterbalanced order, blinded grading, holdout isolation, and captured-only promotion |
| **Optimization evidence provenance** | strong | cryptographic artifact subject and trusted GitHub workflow/source policy; private-repo entitlement remains deployment-specific |
| **Optimization change attribution** | strong | exact hash-bound baseline/candidate configs and deterministic one-path structural diff across all agent layers |
| **Optimization runtime identity binding** | strong | captured trials carry derived whole-variant and per-layer hashes; stale, swapped, missing, or forged bindings fail |
| **Deep research (outlinetodeeptoreport)** | strong | `deep-research.md` + templates + scripts |
| **Browser QA + parallel Playwright** | strong | executable public/quality/auth-read lanes plus guarded iPhone and 320px reflow/zoom gates; standard excludes shared writes; explicit auth-write is credentialed single-worker serial |
| **Browser-agent security receipts** | strong | exact origins, ephemeral auth, URL/data sinks, injection, transfers, permissions, cleanup, evidence |
| **Cross-lane browser evidence** | strong | canonical per-session validation plus account/tenant/worker/namespace uniqueness, overlap, concurrency, artifact-root, cleanup, and review proof |
| **Executable browser-agent guard** | strong | Playwright request blocking, secret-URL checks, popup/download/dialog/error evidence |
| **Durable agent-memory governance** | strong | admission/retrieval/lifecycle receipt; provenance, tenant/subject, contradiction, expiry, deletion-resurrection gates |
| **Cross-CLI coordination transport boundary** | strong | transport-neutral untrusted pointer contract; optional llmquota ring adapter without collector/runtime duplication |
| **Coordination delivery evidence** | strong | executable valid-contract/delegation/artifact output-schema binding with chronology, replay, expiry, acknowledgment, and independent-review gates |
| **Behavioral design** | strong | ethical choice architecture + dark-pattern hard gates |
| **Product marketing / GTM engineering** | strong | launch surfaces, attribution, PQL, CRM feedback |
| **SEO / SEA / AI discovery engineering** | strong | standards-status-aware crawl/index, AI crawler, llms.txt experiment, paid landing, consent, conversion, and retained-revenue gates |
| **Product analytics / KPI contracts** | strong | metric/event/experiment/data-quality contracts |
| **Product-business engineering** | strong | goals to revenue software; standalone scope boundary |
| **Company operating-system engineering** | strong | executive/function interfaces, human-relations safeguards, governance/control model, professional boundaries, integration and assurance |
| **Expo / mobile / GraphQL-first** | deferred | out of core |
| Design + a11y + patterns | done | Tokens, WCAG 2.2, forms/dashboards |
| Frontend RSC / perf / state | done | Compose react-best-practices |
| Backend auth / RLS / actions | done | Core SaaS path strong |
| Stripe + webhooks | done | Unlock-via-webhook correct |
| **Python peer (FastAPI/workers/AI)** | done | `references/python.md` + research/python 44/44 |
| Enforcement + scan + commands | done | 51 commands; PY-*; rate-limit scan + template; `--json`/`--quiet` |
| Progressive disclosure / refactor | done | progressive-disclosure structure + Python module |
| Security research corpus | done | Expanded 2026-07-13 |
| Multi-tenant orgs | done | `backend-multitenant.md` |
| Background jobs (TS + tiers) | done | `background-jobs.md` + python workers |
| OTel runbook | done | observability + `templates/lib/instrumentation.ts` |
| Playwright templates | done | desktop/mobile/auth/quality projects + isolated worker fixtures |
| Rate-limit enforcement | done | scan WARN/FAIL + exempt comment |
| Composition contracts | done | `composition.md` (gstack/unmachined/…) |
| Plan to Validate to Execute | done | plan schema + `validate-plan.sh` |
| Stack pin matrix | done | `COMPAT.md` |
| pgvector / AI product | strong | `backend-pgvector.md` + ai-boundary + multitenant RLS |
| Audit log | done | `audit-log.md` |
| Seat billing | done | `billing-seats.md` |
| Scan fixtures / eval harness / health | done | test-scan, run-evals (static + opt-in `--live` model smoke), engineer-health |
| Multi-host installer | done | hermes/opencode/gemini optional |
| Mobile / Expo | deferred | Out of core |
| Research footers on leaves | done | Leaf modules footered 2026-07-13 |

---

## Coverage matrix by domain

### Design

| Topic | Status | Module(s) |
|---|---|---|
| Tokens / OKLCH / Tailwind v4 | done | design-system, stack-rules |
| Accessibility WCAG 2.2 | done | design-accessibility |
| Forms, dashboards, layout | done | design-patterns |
| Conversion / landing UI | done | conversion-ui |
| Motion system / density | strong | `design-motion.md` (2026-07-14) |
| Storybook | done optional | storybook-dx |

### Frontend

| Topic | Status | Module(s) |
|---|---|---|
| RSC / client boundaries | done | frontend |
| Performance / CWV | done | frontend-performance |
| State architecture | done | frontend-state |
| Streaming / Suspense | done | frontend-streaming |
| Testing pyramid | strong | frontend-testing + Playwright templates + CI counts |
| i18n next-intl | done | frontend-i18n |
| Playwright auth setup template | done | templates/playwright/ |
| Cache tag registry template | strong | data-layer + `templates/lib/cache-tags.ts` (content/rag tags) |

### Backend

| Topic | Status | Module(s) |
|---|---|---|
| SSR auth / middleware | done | backend-auth |
| Migrations / RLS basics | done | backend-database |
| Multi-tenant orgs / invites / roles | done | backend-multitenant |
| Server Actions + Zod | done | backend-api |
| Rate limiting (docs) | done | backend-api + enforcement |
| Rate limiting (CI enforce) | done | engineer-scan --backend/--strict |
| Storage uploads | done | backend-storage |
| Webhooks | done | backend-webhooks |
| pgTAP testing | done | backend-testing |
| Background jobs / queues | done | background-jobs |
| Realtime auth depth | strong | data-layer Realtime auth/RLS (2026-07-14) |
| Audit log pattern | strong | `audit-log.md` |
| Full-text search (FTS) | strong | `backend-fts.md` (2026-07-14) |
| Admin / impersonation | strong | `backend-admin.md` (2026-07-14) |

### Billing & growth

| Topic | Status | Module(s) |
|---|---|---|
| Checkout / Portal / entitlements | done | billing-stripe |
| Seat / org billing | strong | `billing-seats.md` + multitenant |
| Metered billing | strong | `billing-metered.md` (2026-07-14) |
| Feature flags / kill switch | strong | `feature-flags.md` deepened (kill switch, lifecycle) |
| PLG funnels / activation | done | growth-funnels |
| Product onboarding UI | done | product-onboarding |
| Lifecycle email depth | strong | email-notifications (behavioral drip + dunning 2026-07-14) |
| PQL / sales handoff | strong | growth-funnels § PQL (module present) |

### Ops & quality

| Topic | Status | Module(s) |
|---|---|---|
| Deploy Vercel | done | deploy-ops |
| Observability Sentry | done | observability |
| OpenTelemetry setup | done | observability + templates/lib/instrumentation.ts |
| Security headers / CSP | done | backend-security |
| Security research depth | done | security-research (expanded) |
| Infra hardening below app layer (IAM, network, SSH/VPS, containers, backups) | done | infra-security (2026-07-16) |
| Long-horizon session degradation + ongoing/cron agent patterns | done | long-horizon-agents (2026-07-16; agent-longevity-research corpus) |
| Compliance framework → control mapping (SOC 2 / ISO 27001 / GDPR) | done | compliance-controls (2026-07-16; mapper only, certification routes to governance/counsel) |
| GDPR export/delete | done | compliance-privacy |
| Feature flags | done | feature-flags |
| SEO metadata | done | seo-metadata |
| Enforcement / CI | done | enforcement, scripts, templates |
| ESLint shared config template | strong | `templates/eslint.config.mjs` + enforcement |
| Monorepo Turbo | done | architecture-monorepo |

### Engineering meta

| Topic | Status | Module(s) |
|---|---|---|
| TypeScript / Zod | done | typescript |
| Coding principles | done | coding-principles |
| Refactoring | done | refactoring |
| System architecture | done | system-architecture |
| API data flows | done | api-data-flows |
| Rust hot paths | done | rust |
| AI agent prompting | done | ai-agents |
| Skill authoring | done | skill-authoring |
| Workflows / loops | done | workflows, commands |
| Human docs | done | docs/ |

### Explicitly out of core / deferred

| Topic | Status | Rationale |
|---|---|---|
| Expo / mobile | deferred | Revisit if monorepo mobile ships 3× |
| pgvector / RAG | strong | `backend-pgvector.md` shipped |
| Rust gRPC | deferred | Low demand |
| GraphQL / tRPC-primary | deferred | Stack choice outside default |
| Clerk / Auth.js first-class | deferred | Supabase-first intentional; adapter note only |
| Desktop Tauri | deferred | Out of scope |

---

## Missing surfaces

Ranked by how often they block real SaaS work:

| # | Miss | Why | Recommended artifact | Priority |
|---|---|---|---|---|
| 1 | Background jobs | Actions timeout; webhooks must enqueue | `references/background-jobs.md` | **done** |
| 2 | Multi-tenant orgs | B2B default data model | `references/backend-multitenant.md` | **done** |
| 3 | OTel instrumentation template | Prod debug without traces fails | `templates/lib/instrumentation.ts` | **done** |
| 4 | Playwright project template | E2E remains aspirational | `templates/playwright/` | **done** |
| 5 | Rate-limit scan / abuse module | Scanner + `templates/lib/rate-limit.ts` | enforcement + template | **done 2026-07-14** |
| 6 | Research footers on leaves | Provenance / progressive disclosure | done done 2026-07-13 | done |
| 7 | Audit log pattern | B2B / compliance | `audit-log.md` | **done** |
| 8 | pgvector + RLS RAG | AI features | `backend-pgvector.md` | **done 2026-07-14** |
| 9 | Seat billing | Org SaaS money path | `billing-seats.md` + multitenant | **done** |
| 10 | CSP reporting pipeline | Headers without feedback | backend-security + executable template | **done 2026-07-15** |
| 11 | Search (FTS) | Common feature | `backend-fts.md` | **done 2026-07-14** |
| 12 | Admin superuser patterns | Support | `backend-admin.md` | **done 2026-07-14** |
| 13 | Expo | Mobile | optional | P2 |

---

## Recommended agent flows (updated)

| Task | Flow |
|---|---|
| Ship to production | deploy-ops to backend-security to observability to enforcement to gstack /ship |
| Add payments | billing-stripe to backend-webhooks to **background-jobs** to backend-database to cso |
| Launch landing | seo-metadata to conversion-ui to growth-funnels to frontend-performance |
| Multi-locale launch | frontend-i18n to seo-metadata to conversion-ui |
| File uploads | backend-storage to backend-api to backend-testing |
| EU privacy | compliance-privacy to **background-jobs** (delete) to backend-security to backend-testing |
| New user onboarding | product-onboarding to growth-funnels to design-patterns |
| Production incident | observability to backend-api to data-layer |
| Org / team feature | **backend-multitenant** to backend-database to backend-auth to billing-stripe |
| Async email / PDF / AI | **background-jobs** to observability to backend-api |
| Monorepo setup | architecture-monorepo to enforcement |
| Setup CI (human) | docs/enforcement-setup to templates/ |
| Refactor structure | refactoring to domain modules to evals/tests |

*(Italic bold modules are P0 candidates not yet in repo.)*

---

## Module inventory (2026-07-13 snapshot)

| Category | Count | Notes |
|---|---|---|
| Design | 4 | + conversion-ui often grouped with growth |
| Frontend | 8 | router + 7 leaves |
| Backend | 15+ | multitenant, fts, admin, pgvector, jobs present |
| Engineering | 8 | + refactoring |
| Growth | 2 | growth-funnels, conversion-ui (+ product-onboarding in ops) |
| Ops / compliance / comms | 7 | deploy, obs, seo, email, onboarding, flags, privacy |
| Quality | 3 | code-quality, enforcement, storybook |
| Agent meta | 2 | ai-agents, skill-authoring |
| Routers / workflows | 3 | project-detect, MANIFEST, workflows |
| Human docs | 7 | docs/ |
| Research corpora | 13 | + deep-2026-07, expanded security |
| Commands | 24 | + refactor |
| Evals | 32 | as of that snapshot |

---

## Changelog of this audit

### Research deepen (2026-07-13)

| Change | Detail |
|---|---|
| Expanded | `security-research.md` stub to full threat model corpus |
| Added | `deep-2026-07.md` multi-domain deepen + misses |
| Rewrote | this gap-audit coverage matrix |
| Identified P0 | jobs, multitenant, OTel template, Playwright template, rate-limit enforce, footers |
| Confirmed strong | design, RSC, RLS basics, Stripe path, enforcement, refactor progressive disclosure |

### Prior (retained)

- OSS prep, commands, workflows
- MANIFEST, skill-authoring, human docs
- i18n, storage, flags, compliance, monorepo
- Security module, billing, deploy, obs, seo, email, onboarding

---

## Research footer compliance

| Status | Modules |
|---|---|
| Has research link | All `references/*` leaves + hubs (2026-07-13) |
| Prefer specific domain links | Hubs still point at domain corpora; leaves point at report/deep/gap |

Do **not** bulk-load research in sessions - footer is progressive disclosure only.

---

## Decision rule (unchanged)

Add or expand a module when:

1. Gap appears in **>=3 real projects**, or
2. Gap is **ship-blocking** for the default stack (Next + Supabase SaaS).

P0 rows above meet (2) for typical B2B. Do not bloat SKILL.md - new modules stay L3 references.

---

## Skill compliance

| Criterion | Status |
|---|---|
| SKILL.md progressive disclosure / thin router | done (license field; operator L2 dump rejected) |
| Third-person description + negative triggers | done |
| MANIFEST canonical catalog | done |
| Evals present | done |
| Human docs separated | done |
| Research not bulk-loaded | done footers point on-demand |
| Security research non-stub | done as of this pass |

---

## Maintenance

- Re-run gap audit every **6 months** or on Next / Supabase / MCP major. Last pass: 2026-08-23.
- After material capability additions, bump the skill minor, evals, MANIFEST, docs, and CHANGELOG together; `validate-repo.sh` guards drift.
- Keep deep corpus dated; retire stale claims with strikethrough + date.
