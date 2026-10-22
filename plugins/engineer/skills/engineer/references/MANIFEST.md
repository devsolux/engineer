# engineer module manifest

**Load on demand** - read only modules needed for the current task.
Do not bulk-load this file or all references at session start.

**Canonical full catalog** (SKILL.md keeps a short high-frequency map only).

**Human documentation**: [docs/README.md](../docs/README.md) (install, verbs, CI setup - not for agent bulk-load)

## Routers (start here)

| File | Load when |
|---|---|
| `project-detect.md` | Every session start |
| `frontend.md` | Any UI/component work |
| `backend-supabase.md` | Any backend/Supabase work |
| `ai-agents.md` | Prompting, agent workflows |
| `ai-security.md` | LLM tools, MCP, skill supply chain, AI ship checklist |
| `mcp-security.md` | MCP server identity, OAuth, capabilities, schemas, roots, sampling, elicitation, and calls |
| `security-audit.md` | Codebase vulnerability hunt: modes, boundary-and-result rule, six phases, three verdicts, sandbox policy, reports (hunters load the catalog and domain companions per wave) |
| `skill-supply-chain.md` | Third-party skill admission, dependency steering, and executable provenance |
| `malware-detection.md` | Obfuscated-dropper taxonomy, regex/AST/sandbox method-tiering, FP doctrine, and where droppers hide (malware / dropper / obfuscated payload / supply-chain implant) |
| `../research/agent-skill-ecosystem-2026-07.md` | Trust-ranked external skill catalogs, specialist packs, and integration decisions |
| `../research/commercial-product-surfaces-2026-07.md` | Commercial surfaces, product operations, RevOps, and strategy-skill ownership boundary |
| `../research/academic-research-skills-review-2026-07.md` | Pinned academic-research skill comparison and selectively adopted integrity patterns |
| `agent-memory.md` | Durable memory admission, retrieval, isolation, lifecycle, and incident invalidation |
| `agent-incident-response.md` | Contain, eradicate, and recover a compromised agent system |
| `browser-agent-security.md` | Agent-controlled browsing, authenticated sessions, downloads, page-derived URL policy |
| `multi-agent-orchestration.md` | Bounded multi-agent graphs, delegation contracts, lanes, joins, and synthesis |
| `ai-boundary.md` | Product ↔ model service shape (TS vs Python) |
| `ai-evals.md` | Eval harness decision matrix (skill bank / promptfoo / Braintrust) |
| `skill-behavior-evals.md` | Captured real-agent skill runs, layered graders, and promotion integrity |
| `engineer-telemetry.md` | Local-first privacy-safe engineer quality and reliability measurement |
| `skill-authoring.md` | Building or optimizing agent skills |
| `capability-promotion.md` | Detecting recurring capability gaps and choosing reuse, extension, project ownership, or a new skill |
| `refactoring.md` | Refactor code or skill structure; tech debt in structure |
| `workflows.md` | Pipelines, outer-loop contract, risk gates, /loop recipes |
| `coordination-transports.md` | Mailbox, ring-bus, and cross-CLI notification trust boundary |
| `coding-agent-hosts.md` | Codex, Claude Code, Hermes, generic-host capability negotiation and Portage handoff |
| `coding-agent-capability-playbooks.md` | Choose native review, remote, parallel, clean-room, automation, extension, and fallback surfaces |
| `autonomous-experimentation.md` | Bounded baseline-change-evaluate-keep/discard loops with protected oracles and ledgers |
| `developer-experience.md` | SDK/API/CLI/plugin/contributor onboarding, time-to-result, recovery, and live journey audits |
| `hermes-agent-integration.md` | Hermes profiles, tools, memory, curator, browser, cron, gateway, security and evidence |
| `deep-research.md` | Outline → parallel deep agents → validated JSON → report |
| `browser-qa.md` | Browser lanes, evidence, mutation safety, E2E promotion |
| `product-business-engineering.md` | Stated business goal → product/revenue system |
| `company-operating-system.md` | Executive, functional, people, finance, legal, governance, and control context for company-system engineering |
| `system-assurance.md` | Product goals and business rules → full-stack tests, debugging, runtime evidence, residual risk |
| `visual-communication.md` | Infographics, blueprints, field notes, editorial visuals, thumbnails, identity, and banners |

## Commands (Cursor slash)

Install: `scripts/install-commands.sh` → `commands/*.md`
Human index: `docs/slash-commands.md`
Load matching command file when user invokes `/engineer-*`.

## Human documentation

| Path | Load when |
|---|---|
| `docs/README.md` | Maintainer install, doc navigation |
| `docs/enforcement-setup.md` | Copy CI/scripts to a project |

Agents: prefer this manifest over bulk-loading `docs/`.

## Design

| File | Load when |
|---|---|
| `design-system.md` | Tokens, color, type, spacing |
| `design-motion.md` | Density, motion tokens, reduced-motion, INP-aware motion |
| `design-accessibility.md` | WCAG 2.2, a11y |
| `design-patterns.md` | Forms, dashboards, layout |
| `design-taste.md` | Distinctive aesthetic, anti-AI-slop UI, named tone + signature |
| `conversion-ui.md` | Landing, CTAs |
| `behavioral-design.md` | Trustworthy behavior design; dark-pattern gates |
| `visual-communication.md` | Information design, editorial-technical forms, cross-surface brand and distribution assets |

## Frontend

| File | Load when |
|---|---|
| `frontend-performance.md` | CWV, images, bundle |
| `frontend-state.md` | State architecture |
| `frontend-streaming.md` | Suspense, loading, errors |
| `frontend-testing.md` | Vitest, RTL, Playwright |
| `browser-qa.md` | Parallel browser coverage + evidence contracts |
| `secure-package-html-preview.md` | Untrusted on-disk package HTML/document previews, sandboxed iframe, asset allowlist |
| `frontend-i18n.md` | next-intl, locales |
| `storybook-dx.md` | Optional Storybook |
| `stack-rules.md` | Tailwind v4, Next 16, shadcn |

## Backend

| File | Load when |
|---|---|
| `backend-auth.md` | SSR auth, middleware |
| `backend-database.md` | Migrations, RLS |
| `backend-storage.md` | File uploads, buckets |
| `backend-testing.md` | pgTAP, integration tests |
| `backend-api.md` | Server Actions, handlers |
| `backend-webhooks.md` | Stripe events |
| `billing-stripe.md` | Checkout, Portal |
| `billing-metered.md` | Usage records, meters, quotas, overage |
| `backend-security.md` | CSP, headers (AI tools → `ai-security.md`; infra layer → `infra-security.md`) |
| `backend-pgvector.md` | pgvector embeddings, RAG RPC, tenant RLS |
| `backend-fts.md` | Postgres full-text search (tsvector, GIN, rank) |
| `backend-admin.md` | Staff support, impersonation, break-glass |
| `data-layer.md` | Cache, queries, realtime, cacheLife presets |

## Engineering & architecture

| File | Load when |
|---|---|
| `typescript.md` | Types, Zod |
| `coding-principles.md` | Craft, SOLID |
| `refactoring.md` | Behavior-preserving structure change (code + skills) |
| `code-quality.md` | Pre-ship review checklist |
| `system-architecture.md` | Monolith, services |
| `rust.md` | Axum services |
| `python.md` | FastAPI services, workers, AI boundary, uv/ruff |
| `api-data-flows.md` | Cross-service flows |
| `architecture.md` | Single-app layout |
| `architecture-monorepo.md` | Turbo workspaces |

## Ops, growth, quality

| File | Load when |
|---|---|
| `deploy-ops.md` | Vercel, releases |
| `cloud-aws.md` | AWS identity (OIDC/IAM), Lambda/Fargate/App Runner, S3/RDS/DynamoDB/Secrets, CloudFront/API GW/VPC, limits, pricing, cost guardrails |
| `cloud-gcp.md` | GCP identity (WIF/service accounts), Cloud Run, GCS/Cloud SQL/Firestore/Pub/Sub/Secret Manager, network, limits, pricing, cost guardrails |
| `cloud-vercel.md` | Vercel runtime (Fluid compute, runtimes, ISR, cron), deploy model, security/observability, limits, pricing, spend cliffs (extends deploy-ops) |
| `cloud-platforms-iac.md` | Platform selection matrix, Cloudflare Workers/Pages/R2/D1, Fly/Railway/Render/Netlify, IaC (Terraform/OpenTofu/Pulumi/SST/CDK), cross-provider secrets/OTel/FinOps |
| `git-signing-deploy.md` | Commit signatures, GitHub verification, co-authors, signed-commit rulesets, deploy provenance |
| `oss-maintainer.md` | OSS community, governance, security, contribution, release, sustainability and succession operations |
| `observability.md` | Sentry, tracing |
| `background-jobs.md` | Queues, workers, webhook→job, retries |
| `backend-multitenant.md` | Orgs, memberships, roles, invites, RLS helpers |
| `audit-log.md` | Append-only audit events, RLS, retention |
| `infra-security.md` | Cloud IAM, network exposure, SSH/VPS and container hardening, production secrets, backup/DR |
| `compliance-controls.md` | SOC 2 / ISO 27001 / GDPR framework-to-control mapping, gap register, evidence discipline |
| `billing-seats.md` | Org seat quantity, invite gates, Stripe |
| `seo-metadata.md` | SEO, sitemap |
| `web-discovery-engineering.md` | Technical SEO, SEA, AI/LLM discovery, crawler controls, robots, sitemaps, IndexNow, llms.txt, measurement |
| `email-notifications.md` | Transactional email |
| `product-onboarding.md` | Activation UI |
| `compliance-privacy.md` | GDPR export/delete |
| `feature-flags.md` | Rollouts |
| `growth-funnels.md` | PLG funnels |
| `product-marketing.md` | Positioning brief → factual launch surfaces |
| `gtm-engineering.md` | Attribution, identity, PQL, CRM feedback loops |
| `campaign-funnel-integration.md` | Campaign/trial/waitlist overlays on the canonical existing funnel; request-time attribution; overlay-before-new-route |
| `product-analytics.md` | KPI tree, events, experiments, data quality |
| `prd-to-evidence.md` | PRD, goal, acceptance, plan, and evidence traceability |
| `agentic-engineering.md` | Bounded tool loops, orchestration, checkpoints, stop gates |
| `long-horizon-agents.md` | Session degradation model, context budgets, compact/restart/handoff, externalized state, ongoing/cron agents |
| `coding-agent-hosts.md` | Host/surface detection, native adapters, effective authority, cross-host evals and handoffs |
| `coding-agent-capability-playbooks.md` | Task-to-host-surface selection, review ladder, clean-room diagnosis, extensions, and fallback discipline |
| `hermes-agent-integration.md` | Nous Hermes Agent runtime integration and hardening |
| `prompt-optimization.md` | Eval-driven prompt, context, harness, and loop optimization |
| `autonomous-experimentation.md` | General metric-driven agent experiments, resource budgets, ledgers, and promotion |
| `developer-experience.md` | Developer journeys, quickstarts, tooling errors, live audits, and regression evidence |
| `agent-red-teaming.md` | Authorized defensive agent threat modeling and regression testing |
| `security-attack-classes.md` | Hunting catalog: core attack classes, wildcard, and the obvious-things checklist with per-class validation rules |
| `security-audit-domains.md` | Domain companions for the hunt: web/auth, client-side, AI/agent/MCP, supply chain, cloud, protocols/messaging, availability, data isolation |
| `output-quality.md` | Scoped unmachined composition, anti-slop, and detection limits |
| `decision-engineering.md` | Bounded multi-perspective engineering decisions and Council composition |
| `epistemic-honesty.md` | Sycophancy/calibration/hallucination mechanism + correction-flip guard, calibrated abstention, and verification-independence behaviors |
| `product-business-engineering.md` | Revenue/business goal → software architecture |
| `company-operating-system.md` | Accepted company policy → authority, controls, workflows, evidence, and accountable software |
| `portfolio-context.md` | Workspace/venture truth sources, repo→venture resolution, cross-repo impact, hold escalation |
| `system-assurance.md` | Whole-product business logic, layered verification, cross-system debugging, assurance limits |
| `implementation-completeness.md` | Ambiguity resolution, anti-placeholder production rules, and false-done prevention |
| `root-cause-engineering.md` | Fix diagnosis contract, symptom-patch prohibition, declared mitigations, fix-time architecture gates |
| `code-quality.md` | Pre-ship review |
| `enforcement.md` | Enforcement tiers, project setup, CI wiring, maturity model |
| `enforcement-rules.md` | Exact rule catalog: scanner rules, lint configs, a11y/auth/RLS gates, rule→enforcement maps |
| `deep-research.md` | Engineering deep research (outline → deep → report) |
| `web-search-modules/*` | Source strategy packs for research agents |

## Scripts & templates

| Path | Load when |
|---|---|
| `scripts/engineer-scan.sh` | Policy scan (`--strict` `--backend` `--json` `--quiet`) |
| `scripts/scan-false-done.sh` | False-done scanner on the changeset (`--base` `--staged` `--strict` `--json`); BLOCKs skipped tests + not-implemented markers |
| `scripts/rebind-skill-eval.py` | Rebind the skill-eval sample hash chain to the current SKILL.md/runtime after a version bump (`--check` gates drift; `--root` for tests) |
| `scripts/test-scan.sh` | Fixture tests for scanner |
| `scripts/test-scan-false-done.sh` | Fixture tests for the false-done scanner |
| `scripts/test-rebind-skill-eval.sh` | Fixture tests for the skill-eval rebinder |
| `scripts/test-research.sh` | Research validator/report fixtures |
| `scripts/test-repo-validation.sh` | Negative fixtures for command/manifest/version drift |
| `scripts/test-playwright-template.sh` | Consumer install/config fixture for E2E templates |
| `scripts/test-product-metrics.sh` | Measurement contract adversarial fixtures |
| `scripts/test-agentic-contract.sh` | Agentic execution contract adversarial fixtures |
| `scripts/validate-agentic-trajectory.py` | Execution trace policy and evidence validator |
| `scripts/validate-agentic-completion.py` | Contract oracle, captured artifact, verification command, provenance, and completion-decision validator |
| `scripts/test-agentic-completion.sh` | Binding, artifact, oracle, command, review, and false-completion adversarial fixtures |
| `scripts/validate-optimization-run.py` | Evidence-bound paired comparison, trusted attestation, and promotion gates |
| `scripts/test-optimization-run.sh` | Comparative optimization and trial-evidence adversarial fixtures |
| `scripts/validate-security-eval-catalog.py` | Defensive agent threat-coverage and fixture-safety validator |
| `scripts/test-security-eval-catalog.sh` | Defensive security-catalog adversarial fixtures |
| `scripts/validate-security-findings.py` | Security-audit findings receipt validator: three verdicts, derived fingerprints, independence, bound evidence, ledger cross-check |
| `scripts/validate-security-coverage.py` | Security-audit coverage-ledger validator: derived unit ids, status rules, waves, cross-product completeness, carry-forward |
| `scripts/security-ledger.py` | Trusted parent-side ledger tool: init, assign, promote (regular-file/size/JSON/assigned-unit checks), gap, finish |
| `scripts/test-security-findings.sh` / `test-security-coverage.sh` / `test-security-ledger-tool.sh` | Security-audit validator and ledger-tool mutation fixtures |
| `scripts/test-github-signing.sh` | GitHub signing and exact-SHA deploy-gate fixture checks |
| `scripts/test-csp-reporting.sh` | CSP parser, minimization, origin-admission, and header fixtures |
| `scripts/audit-oss-repo.py` | Offline proportional OSS baseline receipt with explicit external-state limits |
| `scripts/test-oss-maintainer.sh` | OSS maintainer rule and receipt fixtures |
| `scripts/apply-oss-baseline.py` | Plan/apply safe non-overwriting public-repository baseline files |
| `scripts/check-oss-leaks.sh` | Private-context leak gate for public-repo changesets (staged default; `--all`; `--ref`; local marker layer; `--public-only`) |
| `scripts/test-oss-leaks.sh` | Runtime leak fixtures: secret/path/infra (incl. cloud identifiers)/personal/marker classes, severity tiers, scopes, visibility skip |
| `scripts/oss_dependency_policy.py` | Bounded repository-aware Dependabot detection and rendering policy |
| `scripts/validate-oss-application.py` | Replay OSS template, target-state, conflict and decision receipt claims |
| `scripts/test-action-runtime-pins.sh` | Immutable GitHub Action and Node 24 runtime fixtures |
| `scripts/test-eval-bank.sh` | Static eval-bank negative fixtures |
| `scripts/validate-skill-eval-run.py` | Captured behavioral-run provenance, grader, and promotion validator |
| `scripts/test-skill-eval-run.sh` | Behavioral-run integrity and adversarial fixtures |
| `scripts/run-live-evals.py` | Opt-in live model-in-the-loop routing smoke via `claude -p` with skills-off baseline |
| `scripts/test-live-evals.sh` | Offline fixtures for the live eval runner |
| `scripts/grade-skill-eval-capture.py` | Deterministically grade a validated capture with a sealed oracle |
| `scripts/validate-skill-eval-grade.py` | Canonical replay of a deterministic skill-eval grade receipt |
| `scripts/compare-skill-eval-grades.py` | Compile paired baseline/candidate grade receipts into a promotion report |
| `scripts/validate-skill-eval-comparison.py` | Validate and replay a paired skill-eval comparison report |
| `scripts/test-skill-eval-grading.sh` | Grading determinism, oracle-binding, and comparison adversarial fixtures |
| `scripts/install-host-activation.py` | Bounded idempotent Engineer routing-rule install for local CLI hosts |
| `scripts/test-host-activation.sh` | Host-activation install, idempotency, and boundary fixtures |
| `scripts/validate-agentic-contract.py` | Agentic execution contract policy validator |
| `scripts/validate-capability-promotion.py` | Capability ownership and skill-promotion decision validator |
| `scripts/test-capability-promotion.sh` | Promotion forgery, signal, catalog, authority, and lifecycle fixtures |
| `scripts/validate-product-metrics.py` | Product measurement plan validator (formula, source, owner, decision rule) |
| `scripts/run-browser-lanes.py` | Compile and optionally execute a bounded multi-lane Playwright plan |
| `scripts/validate-browser-lane-execution.py` | Raw multi-lane Playwright execution receipt and artifact validator |
| `scripts/test-browser-lane-execution.sh` | Lane execution forgery, artifact, and boundary fixtures |
| `scripts/test-evidence-input-boundary.sh` | Evidence-path input confinement adversarial fixtures |
| `scripts/test-evidence-output-boundary.sh` | Evidence-path output confinement adversarial fixtures |
| `scripts/capture-skill-eval.py` | Compile or execute sealed least-privilege Codex/Claude eval jobs |
| `scripts/prepare-skill-eval-baseline.py` | Generate validated no-execution Codex/Claude baseline jobs from live host evidence |
| `scripts/validate-skill-eval-batch.py` | Verify complete hash-bound host, scenario, and activation-mode preparation coverage |
| `scripts/test-skill-eval-batch.sh` | Partial publication, lock, collision, coverage, hash, and path adversarial fixtures |
| `scripts/test-skill-eval-capture.sh` | Cross-host command, isolation, leakage, and consent fixtures |
| `scripts/validate-skill-eval-capture.py` | Job/host/execution/artifact-bound cross-host capture and secret-review validator |
| `scripts/test-skill-eval-capture-manifest.sh` | Capture forgery, path, secret, false-success, and grading-separation fixtures |
| `scripts/record-engineer-telemetry.py` | Explicitly derive a local metadata-only event from a valid capture |
| `scripts/validate-engineer-telemetry.py` | Reject content, identity, remote export, invalid quality state, and malformed events |
| `scripts/summarize-engineer-telemetry.py` | Local capture, grading, error-class, host, and duration summary |
| `scripts/test-engineer-telemetry.sh` | Telemetry privacy, derivation, validation, and summary adversarial fixtures |
| `scripts/capture-host-capabilities.py` | Secret-safe installed Codex, Claude, Grok, Hermes, and Portage surface inventory |
| `scripts/engineer-doctor.py` | Cross-host installed version/hash/mode, host inventory, and eval-readiness report |
| `scripts/test-engineer-doctor.sh` | Current, missing, stale, copy/symlink, and privacy fixtures for doctor |
| `scripts/validate-host-capabilities.py` | Strict host identity, capability vocabulary, hash, context, limitation, and inventory-only validator |
| `scripts/test-host-capabilities.sh` | Host spoofing, capability, path, leakage, limitation, and false-authorization fixtures |
| `scripts/engineer-output-gate.sh` | Resolve unmachined and scan human-facing text/UI |
| `scripts/test-output-gate.sh` | Anti-slop text/UI gate fixtures, including critical-only failures |
| `scripts/scan-doc-supply-chain.py` | Executable Markdown and immutable GitHub Action policy scanner |
| `scripts/test-doc-supply-chain.sh` | Remote-pipe, floating-runner, mutable-Action, and false-positive fixtures |
| `scripts/validate-skill-admission.py` | Candidate tree, provenance, behavior, review, and trust-decision validator |
| `scripts/test-skill-admission.sh` | Skill admission forgery, shadow behavior, self-review, and symlink fixtures |
| `scripts/validate-agent-incident.py` | Agent incident evidence, containment, recovery, and closure validator |
| `scripts/test-agent-incident.sh` | Incident forgery, ordering, persistence, recovery, and false-closure fixtures |
| `scripts/validate-orchestration-contract.py` | Multi-agent graph, authority, lane, budget, join, trace, and review validator |
| `scripts/test-orchestration-contract.sh` | Cycle, escalation, collision, overspend, trace, and self-review fixtures |
| `scripts/validate-orchestration-run.py` | Bound contract, worker, span, authority, budget, join, provenance, and review validator |
| `scripts/test-orchestration-run.sh` | Forgery, orphan, lease, budget, authority, lane, trace, join, and false-pass fixtures |
| `scripts/validate-browser-session.py` | Browser origins, auth, URLs, actions, transfers, injection, artifacts, and cleanup validator |
| `scripts/test-browser-session.sh` | Profile, auth, URL, egress, mutation, popup, transfer, injection, and false-pass fixtures |
| `scripts/validate-browser-lane-run.py` | Aggregate browser worker identity, ownership, overlap, concurrency, artifact, cleanup, and review validator |
| `scripts/test-browser-lane-run.sh` | Cross-lane collision, drift, overlap, path, budget, review, and false-pass fixtures |
| `scripts/validate-agent-memory.py` | Memory provenance, scope, retrieval, lifecycle, review, and decision validator |
| `scripts/test-agent-memory.sh` | Memory poisoning, isolation, authority, retention, deletion, and false-admission fixtures |
| `scripts/validate-coordination-envelope.py` | Valid-contract, delegation, receiver output-schema, artifact, chronology, acknowledgment, and review validator |
| `scripts/test-coordination-envelope.sh` | Injection, spoofing, replay, expiry, path, digest, quota, and false-acceptance fixtures |
| `scripts/validate-mcp-session.py` | MCP OAuth, capability, captured tools/list, tool policy, call, regression, and trust validator |
| `scripts/test-mcp-session.sh` | Audience, token, scope, root, capability, snapshot drift, egress, timeout, deprecated-feature flag, missing-discovery, and false-trust fixtures for both revisions |
| `scripts/validate-mcp-content.py` | Session-bound MCP resource, template, prompt, render, completion-policy, and trust validator |
| `scripts/test-mcp-content.sh` | Catalog drift, URI, content, prompt injection, binding, traversal, review, and false-trust fixtures |
| `scripts/compile-mcp-transcript.py` | Offline redacted JSON-RPC lifecycle, pagination, and deterministic MCP evidence compiler (2025-11-25 handshake and 2026-07-28 stateless shapes) |
| `scripts/test-mcp-transcript.sh` | Lifecycle, protocol, session, capability, response, secret, cursor, manifest, and output-forgery fixtures; stateless `_meta` version, mixed-version, `resultType`, session-header, cache, discovery, task, and deprecated-exposure fixtures |
| `scripts/run-evals.sh` | Static eval bank harness (smoke/full) |
| `scripts/evidence_path.py` | Shared lexical confinement and symlink-component rejection for hash-bound evidence |
| `scripts/check-trajectory-fixture.py` | Offline agent path/fixture checker |
| `templates/fixtures/trajectory-fix-typecheck.json` | Sample trajectory fixture |
| `scripts/engineer-health.sh` | Target-app health score (tsc/lint/test/scan) |
| `scripts/check-rls-migration.sh` | Migration RLS gate |
| `scripts/validate-plan.sh` | Plan → Validate → Execute gate (single plan; `--all` sweep with hygiene warnings; `--completion` drift gate; claims + staleness advisories; primary-worktree anchor resolution) |
| `scripts/test-plan-complexity.sh` | Negative fixtures for proportionality, SOLID pressure, runtime expansion, reversibility, plan-lifecycle fields, integration/completion gate, claims, drift, staleness, and worktree anchor |
| `scripts/plan-fleet-status.sh` | Read-only fleet overview of active plans across canonical workspace repos (`--json`; `--snapshot` → control-plane `data/plan-fleet.json`; anchor-aware, flags duplicate clones) |
| `scripts/test-plan-fleet.sh` | Fleet fixtures: policy walk, collisions, stale streams, orphaned plan/ branches, worktree/duplicate-clone findings, JSON shape, graceful degrade |
| `scripts/validate-repo.sh` | First-party skill integrity |
| `scripts/install-all-agents.sh` | Multi-host skill install (`--hosts`) |
| `scripts/research-validate-json.py` | Deep-research field, uncertainty, claim, source, URL, and date evidence gate |
| `scripts/research_contract.py` | Shared deep-research configuration and symlink-safe path resolver |
| `scripts/research-validate-topic.py` | Deep-research topic coverage, cutoff, confinement, identity, and cross-item source consistency gate |
| `scripts/research-init-review.py` | Derive a non-authorizing semantic-review draft from current claims and hashes |
| `scripts/research-validate-review.py` | Hash-bound semantic claim-review and captured-evidence validator |
| `scripts/research-report.py` | Evidence-revalidated deep-research results → report.md |
| `templates/github/engineer-gates.yml` | CI setup |
| `templates/supabase/tests/` | pgTAP starter |
| `templates/playwright/` | Parallel-safe desktop/mobile/auth/quality E2E |
| `templates/playwright/safe-browser.ts` | Runtime origin, URL-secret, popup, download, dialog, request, and error guard |
| `templates/playwright/mobile-quality.spec.ts` | Compact reflow, page-overflow, viewport, and zoom quality gate |
| `templates/playwright/mobile-quality.ts` | Deterministic viewport policy parser for compact browser tests |
| `templates/product-metrics/` | KPI, event, privacy, and experiment contract |
| `templates/agentic/` | PRD-to-loop execution contract and schema |
| `templates/agentic/prompts/` | Copy-paste agent prompt bodies (feature build, bug fix, audit only, plan only, security hunter / coverage critic / verifier / record reviewer) |
| `templates/agentic/completion-receipt.sample.json` | Contract-bound final acceptance and independent completion decision receipt |
| `templates/agentic/completion-evidence/verification.json` | Synthetic captured command and behavioral acceptance evidence |
| `templates/agentic/optimization-run.sample.json` | Repeated baseline/candidate optimization receipt |
| `templates/agentic/optimization-evidence/trials.json` | Captured paired trial outputs, traces, graders, seeds, and order fixture |
| `templates/agentic/optimization-evidence/variants.json` | Full baseline/candidate configs for deterministic changed-layer attribution |
| `templates/agentic/optimization-attestation-policy.sample.json` | External trusted repository, workflow, source-ref, predicate, issuer, and runner policy |
| `templates/github/optimization-attestation.yml` | Fixed-path GitHub OIDC/Sigstore attestation workflow for captured trial evidence |
| `templates/agentic/security-eval-catalog.sample.json` | Authorized isolated agent-security evaluation catalog |
| `templates/agentic/security-findings.sample.json` | Illustrative security-audit findings receipt (one record per verdict, one hardening note) |
| `templates/agentic/security-coverage.sample.json` | Illustrative security-audit coverage ledger (12 units, one wave, distinct critic) |
| `templates/agentic/security-audit-evidence/` | Bound architecture brief, report, and evidence excerpts for the security-audit samples |
| `templates/agentic/security-findings.schema.json` / `security-hunter-result.schema.json` | JSON Schema consumer aids for the findings receipt and the hunter result (not the enforcement path) |
| `templates/github/verified-deploy-gate.yml` | Reusable fail-closed exact-SHA GitHub verification gate |
| `templates/github/oss-maintainer-baseline.md` | Proportional OSS maintainer evidence and exception receipt |
| `templates/security/csp-reporting.ts` | Privacy-minimized modern and legacy CSP report parser/handler/header helper |
| `templates/agentic/skill-eval-run.sample.json` | Captured real-agent output, trace, graders, and release decision |
| `templates/agentic/skill-eval-job.sample.json` | Hash-bound scenario and cross-host capture policy |
| `templates/agentic/skill-eval-capture.sample.json` | Ungraded job/host/artifact-bound capture manifest fixture |
| `templates/agentic/host-capabilities.sample.json` | Non-authorizing coding-agent host inventory fixture |
| `templates/agentic/skill-admission.sample.json` | Complete third-party skill admission and trust-decision receipt |
| `templates/agentic/agent-incident.sample.json` | Agent incident response and staged recovery receipt |
| `templates/agentic/orchestration-contract.sample.json` | Bounded multi-agent delegation and execution policy |
| `templates/agentic/orchestration-run.sample.json` | Captured multi-agent runtime behavior and synthesis receipt |
| `templates/agentic/browser-session.sample.json` | Agent-controlled browser session policy and observed evidence receipt |
| `templates/agentic/browser-lane-run.sample.json` | Hash-bound aggregate receipt for parallel browser session lanes |
| `templates/agentic/agent-memory.sample.json` | Durable memory admission, retrieval, lifecycle, and review receipt |
| `templates/agentic/coordination-envelope.sample.json` | Cross-CLI transport notification bound to a delegation and local artifact |
| `templates/agentic/mcp-session.sample.json` | MCP server authorization, capabilities, tools, calls, tests, and review receipt |
| `templates/agentic/mcp-evidence/tools-list.json` | Captured synthetic MCP tools/list artifact used to derive reviewed schema hashes |
| `templates/agentic/mcp-content.sample.json` | Session-bound MCP resource and prompt content admission receipt |
| `templates/agentic/mcp-evidence/server-content.json` | Captured synthetic resource catalogs, reads, prompt catalogs, and renders |
| `templates/agentic/mcp-evidence/transcript.jsonl` | Redacted ordered synthetic MCP JSON-RPC capture |
| `templates/agentic/mcp-evidence/capture-manifest.json` | Deterministic transcript provenance and semantic output hashes |
| `templates/agentic/mcp-session-2026-07-28.sample.json` | MCP 2026-07-28 stateless session receipt with `deprecated_feature_exposure` acknowledgement |
| `templates/agentic/mcp-content-2026-07-28.sample.json` | Content admission receipt bound to the 2026-07-28 stateless session sample |
| `templates/agentic/mcp-evidence-2026-07-28/transcript.jsonl` | Redacted synthetic 2026-07-28 stateless capture: per-request `_meta`, `server/discover`, `resultType`, cache fields, no session |
| `templates/agentic/mcp-evidence-2026-07-28/capture-manifest.json` | Deterministic stateless transcript provenance, discovered capabilities, deprecated exposure, and output hashes |
| `templates/agentic/mcp-evidence-2026-07-28/tools-list.json` | Compiled two-page synthetic tools/list artifact from the stateless capture |
| `templates/agentic/mcp-evidence-2026-07-28/server-content.json` | Compiled synthetic resource, template, prompt, and completion capture from the stateless transcript |
| `templates/lib/instrumentation.ts` | Next.js OTel bootstrap |
| `templates/lib/cache-tags.ts` | Cache tag registry |
| `templates/plan-artifact.schema.json` | Plan artifact shape (lifecycle: stream, origin incl. sidequest, interrupts, resume_context, verification, integration) |
| `templates/plan.sample.json` | Example multi-file plan (copy to `.engineer/plan.json`, or `.engineer/plans/<slug>.json` per stream) |
| `templates/eslint.config.mjs` | Next flat ESLint config for CI `--max-warnings=0` |
| `templates/lib/rate-limit.ts` | Upstash sliding-window helper for Server Actions |
| `templates/research/*` | Engineering research field/outline presets |
| `composition.md` | Partner skill ownership (incl. the business knowledge/strategy/artifact skill boundary) + portage + gstack loop catalog |

## Research (via module footers only - never bulk-load)

| File | Topic |
|---|---|
| `research/deep-2026-07.md` | Multi-domain deepen + misses (all topics) |
| `research/gap-audit.md` | Coverage matrix + P0-P2 roadmap |
| `research/report.md` | Research index / provenance |
| `research/design-research.md` | Design corpus |
| `research/frontend-research.md` | Frontend corpus |
| `research/backend-research.md` | Backend corpus |
| `research/security-research.md` | App security threat model (CSP, actions, RLS) |
| `research/csp-reporting-2026-07.md` | CSP Level 3, Reporting API, privacy and Next.js rendering tradeoffs |
| `research/oss-maintainer-2026-07.md` | OpenSSF and GitHub maintainer/security/release research |
| `research/oss-safe-application-2026-07.md` | Automatic local OSS remediation and accountable policy boundary |
| `research/github-actions-node24-2026-07.md` | Node 24 action migration, immutable pins, runner and cache policy |
| `research/enforcement-research.md` | Enforcement corpus |
| `research/coding-research.md` | Coding corpus |
| `research/growth-research.md` | Growth corpus |
| `research/ai-agents-research.md` | Agent prompting corpus |
| `research/agent-skills-research.md` | Skill authoring corpus |
| `research/refactoring-research.md` | Fowler + progressive-disclosure refactor corpus |
| `research/python/` | Python peer-language deep corpus (outline + 44 results) |

## Maintainer / CI catalog (skill repo only)

Run inside the engineer repository; target apps never need these.

```bash
bash scripts/validate-repo.sh
python3 scripts/report-module-currency.py          # reference-module review-cadence report (informational; --fail-after-days N gates)
bash scripts/test-scan.sh
bash scripts/run-evals.sh          # smoke
bash scripts/run-evals.sh --full
bash scripts/run-evals.sh --live --compare --model haiku  # opt-in live routing smoke (costs tokens)
bash scripts/validate-plan.sh .engineer/plan.json
bash scripts/validate-plan.sh --all .       # every plan under .engineer/ (plan.json + plans/*.json) + hygiene warnings
bash scripts/validate-plan.sh --completion .engineer/plans/<slug>.json  # drift gate before done (--warn-only mid-flight)
bash scripts/plan-fleet-status.sh           # active-plan fleet across canonical repos (--json | --snapshot)
python3 scripts/validate-agentic-completion.py templates/agentic/completion-receipt.sample.json --evidence-root .
bash scripts/install-all-agents.sh --hosts all
python3 scripts/validate-optimization-run.py templates/agentic/optimization-run.sample.json --evidence-root .
# Captured promotion only: add --verify-attestation
python3 scripts/validate-security-eval-catalog.py templates/agentic/security-eval-catalog.sample.json
python3 scripts/validate-security-coverage.py templates/agentic/security-coverage.sample.json --evidence-root .
python3 scripts/validate-security-findings.py templates/agentic/security-findings.sample.json --evidence-root .
python3 scripts/validate-skill-eval-run.py templates/agentic/skill-eval-run.sample.json
python3 scripts/capture-skill-eval.py templates/agentic/skill-eval-job.sample.json --print-command
python3 scripts/prepare-skill-eval-baseline.py --scenarios 121 --hosts codex,claude --activation-modes explicit,implicit
python3 scripts/validate-skill-eval-batch.py .engineer/eval-jobs/manifest.json --root .
python3 scripts/grade-skill-eval-capture.py capture.json --oracle oracle.json --root . --output grade.json
python3 scripts/validate-skill-eval-grade.py grade.json --root .
python3 scripts/compare-skill-eval-grades.py comparison.json --root . --output report.json
python3 scripts/validate-skill-eval-comparison.py report.json --root .
python3 scripts/record-engineer-telemetry.py grade.json --root . --output .engineer/telemetry/events.jsonl
python3 scripts/summarize-engineer-telemetry.py .engineer/telemetry/events.jsonl
python3 scripts/scan-doc-supply-chain.py
python3 scripts/validate-skill-admission.py templates/agentic/skill-admission.sample.json
python3 scripts/validate-agent-incident.py templates/agentic/agent-incident.sample.json
python3 scripts/validate-orchestration-contract.py templates/agentic/orchestration-contract.sample.json
python3 scripts/validate-orchestration-run.py templates/agentic/orchestration-run.sample.json
python3 scripts/validate-browser-session.py templates/agentic/browser-session.sample.json
python3 scripts/validate-browser-lane-run.py templates/agentic/browser-lane-run.sample.json
python3 scripts/run-browser-lanes.py browser-plan.json --root . --print-commands
python3 scripts/validate-browser-lane-execution.py .engineer/browser-runs/RUN/execution.json --root .
python3 scripts/validate-agent-memory.py templates/agentic/agent-memory.sample.json
python3 scripts/validate-coordination-envelope.py templates/agentic/coordination-envelope.sample.json --root . --artifact-root templates/agentic/coordination-evidence
python3 scripts/validate-mcp-session.py templates/agentic/mcp-session.sample.json --evidence-root .
python3 scripts/validate-mcp-content.py templates/agentic/mcp-content.sample.json --evidence-root .
python3 scripts/compile-mcp-transcript.py --check-manifest templates/agentic/mcp-evidence/capture-manifest.json --evidence-root .
python3 scripts/validate-mcp-session.py templates/agentic/mcp-session-2026-07-28.sample.json --evidence-root .
python3 scripts/validate-mcp-content.py templates/agentic/mcp-content-2026-07-28.sample.json --evidence-root .
python3 scripts/compile-mcp-transcript.py --check-manifest templates/agentic/mcp-evidence-2026-07-28/capture-manifest.json --evidence-root .
bash scripts/engineer-output-gate.sh path/to/human-facing-output.md
```

Deep-research validator invocations (run in the topic directory): `deep-research.md`.

## Repository maintenance

These tools belong to the source repository, not a separate runtime service.

| Tool | Responsibility |
|---|---|
| `build-plugin.py` | Reproducible shared bundle, host metadata, ZIP and drift checks |
| `run-tests.py` | Discover all offline shell/Python suites in isolated source copies |
| `check-source.py` | Source syntax, core links, and marketplace identity |
| `report-module-currency.py` | Reference-module review-cadence report: past due, missing header or cadence; never redates |
| `clean-build.py` | Scoped cleanup of disposable build output |
