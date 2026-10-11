# Autonomous experimentation

**Last verified**: 2026-07-15 · **Review cadence**: 3 months
**Scope**: bounded, measurable code or configuration experiments run by an agent
**Related**: `prompt-optimization.md`, `agentic-engineering.md`, `workflows.md`, `ai-security.md`

Choose this module when an agent repeatedly changes one system, runs a fixed evaluation, and keeps or
discards the candidate. Examples include model training, compiler flags, query plans, prompts, search
ranking, bundle size, latency, or a deterministic product-quality benchmark.

Do not use hill climbing when the metric is subjective, easy to game, causally distant from the user
outcome, or unsafe to optimize without human judgment.

## Experiment contract

Freeze before the first candidate:

| Field | Requirement |
|---|---|
| Goal | One primary metric with direction and units; named guardrails and maximum regressions |
| Oracle | Immutable evaluation code, dataset/split, environment class, seeds, and parsing rules |
| Mutable surface | Exact allowlisted files/config keys; everything else read-only |
| Baseline | Captured from the current revision on the same environment before experimentation |
| Budget | Per-trial and total wall time, cost, compute, memory, attempts, and disk |
| Decision | Predeclared keep/discard/crash/invalid thresholds, including complexity cost |
| Ledger | Append-only trial identity, parent, change, hashes, metrics, resources, status, and reason |
| Stop | Success target, no-progress window, total budget, repeated crash, user interrupt, or risk gate |

The optimizer may propose code, but it may not modify the oracle, ledger history, budgets, stop rules,
protected datasets, dependency set, or security boundary. Place those outside its write lane.

## Loop

1. Verify the repository and environment. Run the untouched baseline first.
2. Choose one attributable idea. Record the hypothesis and expected mechanism before editing.
3. Change only the allowlisted surface. Commit or snapshot the candidate before execution.
4. Run the fixed command with output redirected to a bounded log. Enforce timeout and resource limits
   outside the candidate process.
5. Parse metrics through trusted code. Missing, malformed, non-finite, or partial output is invalid,
   never an improvement.
6. Apply primary metric, guardrail, complexity, and uncertainty rules. Keep only a valid improvement.
7. Record the trial whether kept, discarded, crashed, timed out, or invalid. Preserve the candidate
   digest even when its branch or worktree is removed.
8. Continue from the best eligible parent, or deliberately explore another branch when the search
   policy says so. Stop at the contract limit.

Create a fresh worktree or reversible patch per candidate. Do not use destructive reset in a dirty user
tree. A kept candidate still needs the system's normal tests, security checks, and independent review.

## Comparable evidence

- Fixed wall time answers "best result under this machine-time budget," not "best algorithm." Hardware,
  thermal state, cache, contention, compiler, dependency, and dataset changes break comparability.
- Counterbalance order or repeat trials when warmup, drift, noise, or shared infrastructure matters.
  Report distribution and uncertainty, not only the best observed run.
- Prevent metric gaming: protect evaluation inputs, inspect traces and output artifacts, and add
  secondary correctness/safety oracles. Never optimize on the final holdout repeatedly.
- Charge failures, retries, compile/setup time, and discarded candidates to total search cost even when
  the primary metric excludes them.
- Penalize unjustified complexity. Equal or near-equal performance with less code, fewer dependencies,
  or lower resource use can be a valid win when the rule is declared before the run.

## Autonomy boundary

"Run overnight" authorizes persistence toward the experiment goal. It does not authorize unlimited
spend, indefinite execution, new dependencies, network destinations, production mutation, permission
changes, or rewriting the experiment contract. Use a supervisor-controlled deadline, kill switch,
heartbeat, disk quota, and crash/no-progress circuit breaker.

Production traffic, customer data, paid APIs, external messaging, deploys, destructive operations, and
security experiments keep their normal approval gates. An optimizer cannot approve its own escalation.

## Promotion

Promote the best candidate only after:

- replay from a clean checkout using the recorded candidate and oracle hashes;
- repeated confirmation on the declared evaluation set and untouched holdout;
- ordinary functional, security, accessibility, privacy, and operational gates;
- complexity and maintainability review;
- an independent decision that cites the ledger and rejects contaminated or incomparable trials;
- rollout, monitoring, rollback, and expiry/revisit plan.

The experiment ledger is evidence, not production authorization.

---

Research: `../research/external-agent-methods-2026-07.md` and the optimization research named by
`prompt-optimization.md`.
