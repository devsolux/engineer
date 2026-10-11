# Prompt and loop optimization

**Last verified**: 2026-07-16 · **Review cadence**: 3 months

Optimize the system that produces behavior: instructions, context selection, tools, loop,
model, and graders. Do not attribute every failure to prompt wording.

## Prompt contract

Version prompts as code. Record purpose, inputs, output schema, invariants, examples,
forbidden behavior, tool policy, uncertainty behavior, and compatible model/harness versions.
Keep stable policy separate from per-task data. Put long reference material behind retrieval
or skills and load it only when relevant.

## Diagnose before editing

Classify failed trajectories:

- Missing knowledge or context.
- Conflicting or vague instructions.
- Wrong tool, tool description, or tool result shape.
- Loop/state failure: no checkpoint, stale plan, retry spiral, premature stop.
- Model capability or context-budget limit.
- Broken task, flaky environment, weak grader, or reward loophole.

Change the lowest responsible layer. A prompt cannot make a non-idempotent money mutation
safe or repair a grader that rewards the wrong outcome.

## Harness levers (in order)

Measure first, then pull in order: cache-hit rate → single-step tool reliability → context budgets,
tool-schema design, and subagent isolation. Required harness telemetry: per-turn
`cache_read`/`cache_write`, tool-call success rate, activation rate, and cost per task. Tool schemas
are a behavior lever - names and descriptions drive selection; return concise high-signal responses;
write error messages that state the fix; consolidate multi-step operations; budget the tool count.
Advanced tool use (beta `advanced-tool-use-2025-11-20`, verified 2026-07-16): Tool Search /
`defer_loading` (~85% tool-token reduction - vendor benchmark, unreplicated) and programmatic tool
calling keep intermediate results out of context. Eval-driven tuning treats the harness as the
system under test: frozen task set, paired with-lever/baseline arms, activation-marker plus
assert/forbid grading, pass@N for nondeterministic routing, hard cost caps (`ai-evals.md`).

## Optimization loop

1. Freeze a representative baseline: prompt, model, tools, harness, dataset, and seeds.
2. Split capability, regression, adversarial, and holdout tasks.
3. Define outcome graders plus trajectory, cost, latency, and safety constraints.
4. Inspect failures and propose one attributable change.
5. Run repeated trials; track pass@1 and consistency, not only best-of-many success.
6. Reject gains that regress holdout, safety, cost, or latency beyond their budgets.
7. Read sampled traces for grader gaming and accidental shortcuts.
8. Promote fixed production failures into regression cases.

Attribution is executable, not a label. Put the full baseline and candidate configurations in a
variant bundle with `prompt`, `context`, `tool`, `loop`, `model`, `grader`, and `environment`
sections. Bind its digest in the receipt, declare one allowed JSON pointer beneath the changed
layer, and require the validator's observed recursive diff to equal that pointer exactly. Version
names must match the bundle. Frozen model, temperature, tool manifest, harness, repository fixture,
and resource class must match both variants unless that exact layer is the controlled change.
The captured trial artifact must also repeat canonical whole-variant and per-layer hashes for both
labels. The validator derives these hashes from the bound bundle and requires exact equality, so a
trial set cannot be relabeled onto different prompt, tool, loop, grader, or runtime configuration.

For agents that read external content, include paired hijacking tasks: the same user goal with
benign content and with indirect instructions attempting a forbidden sink. Grade the final state
and emitted tool arguments, not merely whether the response says it resisted the attack.

Use automated prompt search only inside this harness. Never optimize and report on the same
examples. Keep a human-calibrated rubric for subjective quality and an `unknown` outcome when
the grader lacks evidence.

Record a comparison with `templates/agentic/optimization-run.sample.json`, then run:

```bash
python3 scripts/validate-optimization-run.py optimization-run.json --evidence-root . --json
```

Promotion requires one attributable change, identical task/trial pairs, at least three valid
trials per task, disjoint datasets, capability improvement, protected regression and holdout
rates, adversarial safety, cost per success, p95 latency, controlled infrastructure errors, and
independent trace review. The receipt must bind a confined captured trial artifact whose exact path
contains no symlink component and whose records derive every reported result. Validate the path
before resolution and hashing. Baseline and candidate use identical seeds, their execution
order is counterbalanced, graders are blind and independent, and the dataset is frozen before the
candidate. Holdout access is evaluation-only; the optimizer cannot see holdout results before
selection. Infrastructure failures are excluded from behavior scores but remain a separate gate.
Never count cheap early failures as an efficiency improvement.

State the estimand before running: performance on this fixed benchmark, or generalization to a
task population. A fixed task set does not support a population claim. Population claims require
a task-level uncertainty method such as a clustered bootstrap or hierarchical model plus enough
independent tasks to make that analysis meaningful.

An `illustrative_fixture` can validate the contract but cannot authorize promotion. Only a
`captured_run` is promotion-eligible. Captured promotion also requires
`--verify-attestation --attestation-policy <protected-policy.json>`: the GitHub adapter verifies
the exact artifact subject, repository,
signer workflow and revision, source revision and ref, SLSA predicate, hosted-runner policy,
offline bundle, and trusted root. A captured reject receipt may remain unattested while the
bundle is produced. Copy `templates/github/optimization-attestation.yml` to a protected fixed-path
workflow and configure `templates/agentic/optimization-attestation-policy.sample.json` outside the
evidence producer's control. Receipt fields cannot choose a new trusted repository, workflow, or
ref. Private repositories require an eligible
GitHub Enterprise Cloud plan; otherwise configure equivalent trusted provenance and do not
downgrade missing verification into promotion.

A valid signature proves origin and integrity, not recorder or grader correctness. The semantic
trial, holdout, grading, review, and metric gates still apply.

## Context budget

Aim for the smallest high-signal context that supports the next action. Maintain a ledger of
stable facts, decisions, constraints, evidence, and unresolved questions. Compact tool output,
but retain paths and hashes so raw evidence remains recoverable. Remove stale plans after an
explicit supersession record.

## Prompt to production

`PRD → eval tasks → prompt contract → loop contract → baseline → change → repeated trials →
holdout → canary → production traces → regression set`

**Related**: `agentic-engineering.md`, `prd-to-evidence.md`, `ai-evals.md`, `ai-agents.md`

**Research basis**: `../research/agentic-engineering-2026-07.md`, `../research/optimization-evidence-2026-07.md`, `../research/optimization-provenance-2026-07.md`, `../research/optimization-attribution-2026-07.md`, `../research/optimization-runtime-binding-2026-07.md`
