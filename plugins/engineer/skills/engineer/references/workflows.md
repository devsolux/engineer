# engineer workflows, pipelines, and loops

**Last verified**: 2026-08-27 · **Review cadence**: 3 months

End-to-end pipelines invoked via slash commands (`commands/*.md`) or verbs.
Loops compose with Cursor **`/loop`** skill for until-green automation.
This file is the **contract master**: outer loop, stop conditions, budgets,
maker/checker, risk gates, and the multi-file plan rule live here. Pipeline
step-by-step bodies live in their command files (index below).

Human reference: [docs/slash-commands.md](../docs/slash-commands.md)

## Contents
- [Pipeline template](#pipeline-template)
- [Outer-loop contract (binding for agents)](#outer-loop-contract-binding-for-agents)
- [Risk gate table (HITL)](#risk-gate-table-hitl)
- [Multi-file requires a plan](#multi-file-requires-a-plan)
- [Branch-per-plan integration](#branch-per-plan-integration) (+ sidequest protocol)
- [Plan archival & .engineer/ hygiene](#plan-archival--engineer-hygiene)
- [Pipeline index](#pipeline-index)
- [Audit-fix loop (manual)](#audit-fix-loop-manual)
- [Plan → build handoff](#plan--build-handoff)
- [Composition matrix (short)](#composition-matrix-short)
- [Loop type → skill map](#loop-type--skill-map)
- [Anti-patterns](#anti-patterns)

## Pipeline template

Every workflow follows:

```
1. project-detect → references/project-detect.md
2. route modules → SKILL.md routing map (2-4 leaves max)
3. plan (if multi-file) → .engineer/plan.json with proportionality/complexity receipt, validated + approved
4. execute steps → command-file checklist
5. verify → typecheck/lint/tests + engineer-scan --strict (required before "done")
6. published/durable output gate → output-quality + unmachined text/UI scan when in scope
7. compose → gstack / portage / Council when the task warrants it
```

**Verification is not optional** for multi-file or schema work. Rhetoric is not evidence: run the commands and record exit codes.

For published or durable plans, PRDs, audits, reports, docs, UX copy, and UI changes, unmachined is
part of the checker. Routine technical chat, status updates, factual handoffs, debugging, and raw
diagnostics skip this gate unless explicitly requested or always-on configuration includes them.
Run `scripts/engineer-output-gate.sh` on text deliverables and add `--ui <path>` for UI source. If the
scanner is unavailable, record that gap and apply `output-quality.md` manually; do not claim
deterministic anti-slop verification.

## Outer-loop contract (binding for agents)

Coding agents run an **outer loop**. Make it explicit so sessions do not burn tokens or claim false done.

| Phase | What happens |
|---|---|
| 1. Sense | Goal, scope, stack from project-detect |
| 2. Plan | For multi-file / schema / ship: emit or update `.engineer/plan.json`; prove simplest viable design |
| 3. Act | Minimal diffs only; load 2-4 modules |
| 4. Observe | Tool/test output, scan results, CI |
| 5. Critique | Fix from evidence, not vibes |
| 6. Stop | Success, hard fail, or escalate to human |

Agent-loop builders wire additional per-phase obligations (checkpointing, failure
classification, completion receipts): `agentic-engineering.md`.

### Stop conditions (hard)

| Condition | Action |
|---|---|
| All `verify_commands` + scan green + acceptance oracles pass | **Stop success** - report hash-bound evidence |
| Max **5** fix iterations without progress (same error) | **Stop fail** - escalate with blocker |
| Max outer turns: **15** for a single feature session (default) | **Stop** - handoff or ask human (override only if user raises budget) |
| User says stop / abort | **Stop** immediately |
| Risk gate triggered (see table below) | **Pause** until human approve/deny |

### Budgets (defaults)

| Budget | Default | Notes |
|---|---|---|
| Outer turns | 15 | Raise only with user consent |
| Verify-fix rounds | 5 | Then escalate (audit-fix loop) |
| CI poll iterations | 30 × 2m | See loop-ci |
| Token/$ | host policy | Prefer smaller models for explore; strong for plan/critique |

### Maker ≠ checker (default)

Do not let the implementer self-certify alone.

| Role | Who | Does |
|---|---|---|
| **Maker** | Agent that wrote the diff | Implements minimal change |
| **Checker** | Prefer in order below | Proves done with evidence |

**Checker preference (pick first available):**

1. **Deterministic** - `verify_commands` + `engineer-scan --strict` + project tests (required always)
2. **CI** - PR checks green (`/engineer-loop-ci` after push)
3. **Second agent** - separate session or subagent with prompt: "review diff only; do not expand scope; run verify"
4. **Human** - always-ask risk class (prod, migrate, billing)

After maker finishes:

```
[ ] Maker: diff limited to plan files_touch
[ ] Checker: all verify_commands exit 0 (paste evidence)
[ ] Checker: scan --strict exit 0 when enforcement present
[ ] If multi-file feature: CI green or second-agent review noted
[ ] If an execution contract exists: completion receipt resolves every oracle and command
[ ] Only then mark task done / open PR as ready
```

`/engineer-loop-verify` is the automated maker-fix-check cycle; stop conditions still apply.
Green commands are necessary but not sufficient when the contract defines behavioral acceptance.
Deterministic enforcement of "verification is not optional": where the host has a Stop/SubagentStop hook surface, gate "done" behind a hook that blocks until `verify_commands` + scan pass; where it has none, the same gate moves to CI.

For behavior changes, reproduce the failure or write the smallest failing test/check before the fix
when feasible. Watch it fail for the expected reason, make the minimal change, watch it pass, then
refactor without changing behavior. A test that starts green does not prove it covers the change.
Exceptions such as exploratory spikes, generated migrations, or inaccessible external failures must
record the substitute oracle and why red/green was not available.

Review in this order:

1. **Acceptance/spec compliance**: every requirement, boundary, and observable outcome is present; no
   unrequested scope or missing error state.
2. **Code and operational quality**: correctness, maintainability, security, performance, accessibility,
   observability, and proportional complexity.

Do not let a clean implementation pass when it solves the wrong problem. The second stage starts only
after blocking acceptance gaps are resolved.

## Risk gate table (HITL)

Classify before acting. When in doubt, **ask**.

| Class | Examples | Agent behavior |
|---|---|---|
| **never-ask** | Format, typos, comment-only, read-only inspect, run tests/typecheck | Proceed |
| **ask-if-ambiguous** | Multi-file feature shape, public copy tone, non-breaking refactors >3 files | Plan first; ask if two viable designs |
| **always-ask** | Prod deploy, force-push, `git push --force`, DB migrate/drop, secrets/env changes, billing/webhook entitlement logic, public OSS flip, deleting user data, installing unaudited skills/MCP | Present plan + wait for explicit yes |
| **never-do** | Print/paste seed phrases or mainnet keys, commit `.env`, disable RLS "temporarily", enable paid on `success_url` alone | Refuse; explain |

Unattended runtimes (headless `-p`, cron): no human is present, so every **always-ask** class is a fail-closed stop plus a recorded gap - never emulate the gate in a prompt.

Cross-session handoff: use **portage** (not full chat dump) when switching agents. See [composition.md](./composition.md).

## Multi-file requires a plan

If the task touches **>1 file** (or any migration/auth/payment):

1. Run the activation-time plan check (SKILL.md Plan → Validate → Execute): resume a matching
   active plan, or adopt in-flight work retroactively (`origin: "adopted-mid-session"` +
   `resume_context`) - never duplicate a stream or contest a shared `plan.json` another session owns
2. Write the plan from [templates/plan.sample.json](../templates/plan.sample.json) - default
   `.engineer/plan.json`; parallel/multi-session streams get `.engineer/plans/<slug>.json` (one per stream)
3. `bash scripts/validate-plan.sh <plan>` (`--all` sweeps every plan under `.engineer/`)
4. User (or explicit override for tiny fixes) sets `"status": "approved"` - `validate-plan.sh` verifies the status enum, not approver identity, so an unattended `approved` is only as strong as the standing authorization it cites; quote that authorization in `approved_by`
5. Execute only listed `files_touch`; run every `verify_commands` before done; record the
   `verification` receipt and pass the drift gate (`validate-plan.sh --completion <plan>`).
   Done plans stay in place as receipts (30-day archival rule below)

Skip full ceremony for one-line typos and pure docs-only edits.

## Branch-per-plan integration

**Proportionality**: a single stream in a single session works on `main` directly - no branch
ceremony. A branch is **required** the moment a second stream activates in the repo or the plan
is multi-session. Convention: branch `plan/<slug>`, worktree `.worktrees/<repo>/<slug>` (the
workspace registry's durable-worktree layout); state lives in the plan's
optional `integration` object (`branch, worktree, base, rebased_at, merge_commit, merged_at, disposition`).

| Rule | Contract |
|---|---|
| Rebase | On `main` at session start and again before merge; record `rebased_at` |
| Verify | `verify_commands` must pass **after** the final rebase, not only on the stale branch |
| Merge | Serially - one plan branch at a time; record `merge_commit` + `merged_at` |
| Completion gate | `done` + `integration.branch` ⇒ `merge_commit` set and branch deleted, or `disposition: parked`/`discarded` - orphaned `plan/` branches are a finding (validator-enforced) |
| Claims | validate-plan.sh warns when active plans claim the same `files_touch` - an advisory coordination signal, never a lock |
| Anchor | The **primary worktree's** `.engineer/` is the repo's single coordination directory - resolve `git rev-parse --git-common-dir` from any linked worktree or subdirectory cwd. Plan files live at the anchor; `integration.worktree` records where the work happens. A linked worktree's `.engineer/` is a branch checkout, never coordination state (validator and fleet read only the anchor - no double-counting) |
| One checkout | Duplicate full clones of one origin cannot share an anchor and silently fork coordination - plan-fleet-status.sh flags them; workspace policy allows one canonical checkout, extras must be explicit worktrees |

### Sidequest protocol (halt-and-return)

Trigger: the user says **sidequest** (side quest / side-quest). What follows becomes a sub-plan
that must not alter the main plan or the original work. Stack discipline (LIFO):

1. Record the exact halt point (what was in progress, next intended step) in the active plan's
   `resume_context`/`session_notes` - the return address; change nothing else in the main plan
2. Open `.engineer/plans/<slug>.json` with `origin: "sidequest"` + `interrupts: "<parent-stream>"`
3. Main work halts until the sidequest reaches a terminal status, then resume the parent from its
   `resume_context`. Nested sidequests stack (LIFO); warn at depth >2
4. Escape hatch: delegate an independent sidequest to a background agent/separate stream and keep
   working the main plan **only on explicit user choice** - never as the default
5. Trivial detours (one-liner questions, exemption-class fixes) need no sub-plan - handle and return

## Plan archival & `.engineer/` hygiene

Terminal plans (done/verified/completed/abandoned/superseded) stay in place as receipts for **30
days**, then move to `.engineer/plans/archive/` (plain `git mv` - history keeps the receipt).
`.engineer/` holds plan/receipt artifacts only: no scratch files, dumps, or generated assets.
`validate-plan.sh --all` warns on non-plan junk and on >20 unarchived terminal plans; validating a
non-terminal plan warns when `main` moved significantly since `approved_at` (stale plan -
re-validate scope). Fleet overview of active streams across canonical repos:
`scripts/plan-fleet-status.sh` (`--json`; `--snapshot` writes the control-plane-consumed snapshot).

## Pipeline index

Step-by-step bodies, hard gates, and verify bundles live in the command file.
Load the command file plus the first chain module; do not bulk-load the chain.

| Pipeline | Command | Chain | Done when |
|---|---|---|---|
| Greenfield SaaS | `/engineer-greenfield` | system-architecture → architecture → stack-rules (greenfield default scaffold: Tailwind v4 + shadcn/ui) → design-system → backend-database → backend-auth → enforcement → growth-funnels → conversion-ui → frontend | Schema approved, Tailwind v4 + shadcn scaffolded + de-genericized, tokens locked, auth path chosen, enforcement copied |
| Landing launch | `/engineer-landing` | seo-metadata → conversion-ui → growth-funnels → frontend-performance → unmachined copy audit | Metadata, one primary CTA, CWV checklist, analytics stubs |
| Deep research decision | `/engineer-research` `/engineer-research-deep` `/engineer-research-review` `/engineer-research-report` `/engineer-research-add-items` `/engineer-research-add-fields` | outline → parallel deep agents → claim review → report → HITL pick → plan | `report.md` with sources; **no production code until pick**. Presets, `claim_v1` evidence policy, validators, and provenance (Weizhena MIT): `deep-research.md` |
| Prompt / agent-loop optimization | `/engineer-loop-optimize` | freeze variants + datasets → paired trials → derived receipt → gates → independent review → attestation | Receipt passes `validate-optimization-run.py` (promotion adds `--verify-attestation`); full trial/holdout/grader contract: `prompt-optimization.md` |
| Autonomous measured experiment | - (verb flow) | freeze oracle/budget → baseline → one change → evaluate → ledger → keep/discard → independent promotion | Stop gate fired, every attempt in the ledger, protected inputs unchanged, budgets held: `autonomous-experimentation.md` |
| Developer experience journey | - (verb flow) | persona/job → clean quickstart → first result → recovery → live audit → regression | Clean-env journey + recovery tested, docs match shipped behavior: `developer-experience.md` |
| Browser QA | `/engineer-browser` `/engineer-qa` | coverage matrix → isolated lanes → evidence → minimal fix → re-test → Playwright promotion | Required route×role×viewport×state cells pass; every finding has a repro receipt; prod/external mutations always-ask: `browser-qa.md` |
| Product launch | `/engineer-launch` | product-marketing → conversion-ui → behavioral-design → analytics/GTM → perf/a11y/SEO → Playwright → browser QA | Claims have proof, CTA→activation instrumented, KPI owner/formula exists, publish/deploy separately approved |
| Business-ready product system | `/engineer-business` `/engineer-kpi` | product-business-engineering → domain build → analytics contracts → data-quality tests → decision dashboard | Goal has user mechanism, metric formula, guardrails, source, owner, verification |
| Stripe billing | `/engineer-billing` | billing-stripe → backend-webhooks → backend-database → gstack /cso | Checkout server-side, DB entitlements, webhook idempotency, **never grant entitlements on success_url** |
| Auth + form | `/engineer-auth` | design-patterns → frontend → backend-auth → backend-database | `getUser()` on mutations, middleware setAll, RLS, on-blur validation |
| Multi-locale | `/engineer-locale` | frontend-i18n → seo-metadata → conversion-ui | `[locale]` routes, setRequestLocale, hreflang, language switcher cookie |
| File upload | `/engineer-upload` | backend-storage → backend-api → backend-database → backend-testing | Server path generation, Storage RLS, metadata row, pgTAP path test |
| EU privacy | `/engineer-privacy` | compliance-privacy → backend-security → backend-testing | Export + delete flows, consent storage, legal review note |
| Production ship | `/engineer-ship` | deploy-ops → backend-security → ai-security (if AI/MCP) → enforcement → observability → gstack /ship | Env tiers, CSP, `engineer-scan --strict`, post-deploy smoke, Sentry. Prod deploy is always-ask |
| Public/OSS repository | `/engineer-oss` | oss-maintainer audit → safe baseline applicator + receipt replay → re-audit → host-API state checks | Prepends automatically to ship on confirmed OSS repos; external settings/release mutations stay always-ask: `oss-maintainer.md` |
| Verify loop | `/loop dynamic /engineer-loop-verify` | maker fix → checker verify bundle → repeat | Typecheck + lint + scan green; stop after 5 no-progress iterations |
| Ship-ready loop | `/loop dynamic /engineer-loop-ship` | ship checklist → verify + RLS gate → fix gaps → repeat | All ship gates ✅ and scans pass (no deploy unless user asked) |
| CI watch | `/loop 2m /engineer-loop-ci` | `gh` checks → scoped fix → push if approved → repeat | CI green or actionable failure; max 30 iterations (`gh` CLI authenticated) |

**Activation check** (attach to ship / landing): activation event **named**
(growth-funnels), analytics stubs on signup/activation/primary CTA, empty state
points at the activation path.

Loop recipes load the Cursor **`loop`** skill; use **dynamic** mode when failure types vary.
Where determinism lives: a committed SDK/headless script compiling a fixed DAG reproduces; in-session conversational fan-out does not (live-eval pass@2 measured) - commit the orchestration script.

## Audit-fix loop (manual)

Use when quality is unknown: `/engineer-audit <target>` → if Critical > 0, `/engineer-fix <target>` →
verify (typecheck + engineer-scan) → repeat audit (max 3 rounds, then escalate).
**Stop condition**: zero Critical findings + `engineer-scan --strict` passes.

## Plan → build handoff

`/engineer-plan <feature>` → activation check (resume / adopt / new stream - SKILL.md PVE) →
write `.engineer/plan.json`, or `.engineer/plans/<slug>.json` for a parallel stream →
`bash scripts/validate-plan.sh <plan>` → user reviews → "approved" / "engineer plan LGTM" →
status=approved → `/engineer <same feature>` → run verify_commands + engineer-scan --strict →
`validate-plan.sh --completion <plan>` (drift gate) before marking done.

Never skip approval on: migrations, auth, payments, **>1 file** product logic (see multi-file rule). One-line typos exempt.

## Composition matrix (short)

| After pipeline | Also run |
|---|---|
| `/engineer-landing` | `/unmachined` or unmachined skill on copy |
| `/engineer-billing` | gstack `/cso` |
| `/engineer-ship` | gstack `/ship` (+ canary if configured) |
| `/engineer-landing` | react-best-practices if perf audit needed |
| Any UI | `/engineer-design` audit before merge |
| Mid-session provider switch | **portage** pack (composition.md) |
| Hard bug | gstack `/investigate` |

Full partner ownership: [composition.md](./composition.md).

## Loop type → skill map

| Loop | engineer surface | Partner |
|---|---|---|
| Outer agent | **`/engineer-loop-agent`**, this file, ai-agents.md | host agent |
| Verification | loop-verify, enforcement, scan | - |
| CI watch | loop-ci | `gh` |
| Ship / canary | ship, deploy-ops | gstack ship / canary / land-and-deploy |
| Security deep | backend-security, ai-security | gstack cso |
| Browser QA | - | gstack qa / browse |
| Handoff | composition | portage |
| Eval specification regression | `scripts/run-evals.sh`, ai-evals.md | static bank; never call it behavioral proof |
| Skill behavior regression | `validate-skill-eval-run.py`, skill-behavior-evals.md | captured output, trace, outcome, and grader evidence |
| Research | deep-research | partner research* if preferred |

## Anti-patterns

| Don't | Do |
|---|---|
| Run full greenfield for a one-line fix | Match pipeline to scope |
| Loop forever without stop condition | Max iterations + escalate |
| Ship loop without engineer-scan in project | `/engineer-enforce` first |
| Plan and build in one slash command | Separate `/engineer-plan` → approve → `/engineer` |
| Bulk-load all references | 1 router + 2-4 modules per step |
| Claim tests passed without running them | Verification loop with exit codes |
| Paste full chat when switching tools | portage job packet |
| Install random MCP/skills mid-task | AI security checklist (always-ask) |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
