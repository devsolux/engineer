# PRD to evidence

**Last verified**: 2026-07-15 · **Review cadence**: 3 months

Use this module when a request is large enough that implementation can drift from intent.

## Compiler chain

Treat the PRD as an executable input, not a narrative handoff:

`problem → outcomes → requirements → acceptance evidence → plan steps → tests/evals → shipped evidence`

Every requirement gets a stable ID. Every ID must appear in at least one acceptance
criterion and one plan step. Define each criterion with one or more deterministic JSON
oracles over captured local evidence. A claim is complete only when its named artifact
exists, its digest matches, every oracle passes, and the planned verification commands ran.

## Minimum PRD

- Problem and affected user, grounded in observed evidence.
- Desired outcome and measurable success condition.
- Functional requirements with stable IDs.
- Non-functional requirements: security, privacy, accessibility, reliability, latency, cost.
- Non-goals and boundaries.
- Unknowns and assumptions, with an owner or discovery action.
- Rollout, rollback, observability, and migration constraints.

Write acceptance criteria as observable states. “Good UX” is not testable. “A keyboard
user can submit and recover from each validation error” is.

## Readiness gate

Do not compile a plan while a decision-changing unknown is unresolved. Small reversible
unknowns can become explicit plan steps. Irreversible architecture, data loss, money,
permissions, or external publication require a decision gate.

## Traceability

Use `templates/agentic/execution-contract.sample.json`. The validator rejects orphaned
requirements, acceptance without oracles, and plan steps without evidence. Keep prose for
judgment; use the artifact for links, budgets, policies, and stop conditions.

After the trajectory stops, validate `templates/agentic/completion-receipt.sample.json`.
This binds the exact contract, trajectory, repository revisions, scope diff, command results,
and evidence artifacts. A trajectory's `verification_passed` field is provisional until this
receipt resolves the artifacts and evaluates every contract oracle.

## Change control

When requirements change:

1. Update the PRD and record the reason.
2. Recompute affected acceptance criteria, tests, risks, and steps.
3. Mark obsolete evidence; never silently reinterpret an old criterion.
4. Re-run the relevant capability and regression suites.

**Related**: `agentic-engineering.md`, `prompt-optimization.md`, `workflows.md`, `ai-evals.md`

**Research basis**: `../research/agentic-engineering-2026-07.md`
Completion evidence: `../research/agent-completion-evidence-2026-07.md`
