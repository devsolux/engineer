# Implementation completeness and anti-placeholder contract

**Last verified**: 2026-07-16 · **Review cadence**: 2 months
**Related**: `prd-to-evidence.md`, `code-quality.md`, `workflows.md`, `system-assurance.md`

Production implementation is the default. Unless the user explicitly requests a prototype, mockup,
scaffold, spike, test double, or partial phase, deliver the requested bounded behavior with real
integration, persistence, failure handling, security, and verification. Never reduce scope silently.

## Resolve ambiguity before it becomes omission

Translate vague scope words such as complete, optimal, integrated, responsive, secure, working, all,
and production-ready into observable requirements. Inspect repository and product truth first. Ask
only when alternatives materially change behavior or risk; otherwise make and record the safest
supported assumption. Ambiguity never authorizes a mock, placeholder, fake response, no-op, or skipped
edge case.

## Forbidden production substitutions

- Unresolved task/fix markers, `NotImplemented`, empty handlers, ellipses, or comments promising later work.
- Hardcoded sample entities, fake metrics, random success, demo credentials, in-memory state standing
  in for required persistence, or static JSON standing in for a required service.
- Disabled/skipped tests, weakened assertions, swallowed errors, bypassed auth/RLS, permissive fallback,
  fake loading delay, or a feature flag permanently hiding an unfinished path.
- Buttons with no action, forms that only log, links to `#`, dead routes, placeholder copy, fabricated
  screenshots, incomplete responsive/error/empty/loading states, or happy-path-only integrations.
- “For now,” “later,” “future work,” “out of scope,” or “good enough” used to defer requested behavior
  without an explicit user-approved scope change.
- A green visible test obtained by changing tests, fixtures, or the evaluator instead of satisfying the
  outcome; mocks that make the component under test prove its own assumptions.

Existing unrelated debt is not automatically in scope. Record it separately, but any incomplete state
created, exposed, or relied on by the requested change blocks completion.

## Allowed bounded substitutes

Test doubles are allowed inside tests when they isolate a boundary and at least one appropriate
contract/integration/system check proves the real boundary. Synthetic data is allowed when explicitly
labelled, privacy-safe, and not presented as a real product outcome. Explicit prototypes and mockups
must be visibly marked non-production, isolated from production routes and data, carry no false
completion claim, and list the exact behavior needed for promotion.

When an external dependency or credential is unavailable, implement the real adapter and validation,
fail closed with a useful setup error, and verify through an official sandbox, local emulator,
consumer/provider contract, or captured fixture where possible. Never return fake success.

## Completion sweep

Before saying done:

1. Re-read the request and accepted decisions; map every requirement ID to code and evidence.
2. Inspect the diff and affected paths for placeholder markers, mocks outside tests, skipped checks,
   fake data, dead controls, no-op branches, permissive fallbacks, and deferred language.
3. Trace each critical journey across UI, API, auth, data, jobs/vendors, analytics, and recovery.
4. Run focused tests plus affected integration, browser, security, migration, and regression gates.
5. Exercise success, validation, unauthorized/forbidden, empty, loading, error, retry, duplicate,
   timeout, cancellation, responsive, accessibility, and rollback states where applicable.
6. Confirm configuration, migrations, environment examples, generated types, docs, observability,
   cleanup, and feature-flag lifecycle are ready for the requested environment.
7. Report exact verified scope, commands/evidence, and any blocker. A blocker means incomplete, not done.

Passing tests are necessary evidence, not proof of semantic completeness. Recent coding-evaluation
audits show low-coverage tests can accept incomplete or incorrect patches. Use independent acceptance
review and outcome-level evidence, not only implementation-authored tests.

## Independent verification (grader ≠ doer)

The failure this closes is structural: an agent verifies only against the checks it can see, and
drifts from investigating to "wrapping up" as its turn budget runs down — so it declares success
against a subset and is confidently wrong on the rest. Countermeasures, in order of leverage:

1. **Independent re-run.** The completion sweep's checks are re-run by a pass that did not write the
   code — a fresh-context reviewer subagent, or at minimum an execution the implementer did not author
   and cannot have tuned. The writer's own "all tests pass" is evidence to re-verify, never
   self-certification. Self-verification alone is unreliable: a large share of trajectories that
   self-verify still fail, and forcing an agent to write its own tests yields little — agent
   self-tests are mostly observation (print-style) with few real assertions. Correctness comes from
   *independent/hold-out execution*, not from the author grading their own work.
2. **Hold-out check.** Keep at least one acceptance check the implementer did not see or edit; where
   feasible, commit acceptance tests before the implementation so any later edit to them shows in the
   diff and can be reverted. A visible-pass-only run is not the honest measure.
3. **Deterministic false-done scan.** Run `scripts/scan-false-done.sh` on the changeset (in the target
   repo, against the base). BLOCK findings — skipped/focused tests, explicit not-implemented markers —
   mean not done; the `tests-edited-with-implementation` warning triggers the hold-out re-verify above.
   This is the executable enforcement of the *Forbidden production substitutions* list, not a
   substitute for the trace-level sweep.
4. **Requirement → evidence table.** Map every requirement/acceptance ID to the exact command output
   or screenshot that proves it (UI/browser surfaces: the driven-flow evidence from the Fix/optimize
   completion bar). Materialize with `templates/agentic/completion-receipt.sample.json` and replay via
   `validate-agentic-completion.py`. A criterion with no cited evidence is unverified, not done.

Adversarial self-review ("how could this be wrong?") counts only when it produces a **new check that
is actually run** (a failing test, a diff inspection, a browser observation) — not re-graded prose, and
not debate-to-consensus, which can manufacture confident agreement on a wrong answer.

## Completion language

Use "implemented and verified for [bounded scope]" only when every declared gate passes. Use
"partial," "prototype," "blocked," or "not verified" plainly when true. Never describe a scaffold,
mockup, illustrative fixture, or locally green substitute as a full working implementation.

**Research basis**: `../research/llm-implementation-completeness-2026-07.md`
