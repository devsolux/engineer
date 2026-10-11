# AI / skill eval harness matrix

**Last verified**: 2026-07-15 · **Review cadence**: 3 months

Pick one measurement path; do not run five vendors on one app.

Research: `research/behavioral-skill-evals-2026-07.md` + `research/agent-trajectory-evals-2026-07.md`

## Contents
- [Decision matrix](#decision-matrix)
- [Defaults for devsolux portfolio](#defaults-for-devsolux-portfolio)
- [Skill bank (`run-evals.sh`)](#skill-bank-run-evalssh)
- [Behavioral skill run](#behavioral-skill-run)
- [Product AI eval loop](#product-ai-eval-loop)
- [Maker-checker and evals](#maker-checker-and-evals)
- [Deterministic trajectory state machine](#deterministic-trajectory-state-machine)
- [Comparative optimization receipt](#comparative-optimization-receipt)
- [Anti-patterns](#anti-patterns)
- [Related](#related)

## Decision matrix

| Surface | Default harness | When to upgrade |
|---|---|---|
| **engineer skill bank** (this repo) | `bash scripts/run-evals.sh --smoke` / `--full` | Always on CI (static structure; no model cost) |
| **engineer observed behavior** | Captured run + `validate-skill-eval-run.py` | Before claiming a skill release improved agent behavior |
| **Cross-host raw capture** | `capture-skill-eval.py` | Compile sealed Codex/Claude jobs; execution is explicit and cost-acknowledged |
| **Product prompts** (your SaaS) | **promptfoo** (OSS, CI-friendly) or **Braintrust** (hosted traces+evals) | Choose one per app |
| **Agent trajectories** (multi-turn tools) | LangSmith trajectory / Harbor-class / custom path logs | After single-turn goldens exist |
| **Copy / UI slop** | unmachined `scan_text` / `scan_ui` | Marketing surfaces |
| **Plan / JSON contracts** | `validate-plan.sh`, JSON Schema, Zod | Non-LLM structure |
| **Prompt/loop comparison** | `validate-optimization-run.py` | Before claiming a candidate improved |
| **Agent security catalog** | `validate-security-eval-catalog.py` | Injection, social engineering, tool, identity, memory, network, and oversight coverage |

## Defaults for devsolux portfolio

| Repo type | Do this |
|---|---|
| engineer skill package | CI: `run-evals.sh --smoke` (already in validate.yml) |
| Next product with light AI | promptfoo fixtures in CI **or** Braintrust if already on it |
| Multi-agent coding workflows | Trajectory logs + fixture tasks; skill bank for routing |
| No AI features | Skip model evals; keep typecheck/scan/tests |

## Skill bank (`run-evals.sh`)

- **Static** - validates `evals/evals.json` shape and lists scenarios; does **not** call a model.
- Smoke IDs: core routing / ship / schema scenarios.
- Live model scoring is optional and out-of-band (mount SKILL in an agent; use `--list` prompts).
- A green bank means the specification is valid. It is not evidence that an agent executed it.
- The live-eval pattern generalizes to any harness lever: frozen scenario bank, paired
  with-lever/baseline arms, activation-marker + assert/forbid grading, pass@N for nondeterministic
  routing, hard cost caps (`prompt-optimization.md` harness levers).

```bash
bash scripts/run-evals.sh --smoke
bash scripts/run-evals.sh --full
bash scripts/run-evals.sh --list
```

## Behavioral skill run

When the claim concerns actual agent behavior, capture output, tool trace, resulting-state
evidence, hashes, environment identity, and layered graders. Validate the receipt separately:

```bash
python3 scripts/validate-skill-eval-run.py skill-eval-run.json --json
```

Use `references/skill-behavior-evals.md` for contamination, calibration, repeat-trial, and
promotion rules. A behavioral receipt may reference scenarios from the static bank, but it must
retain the actual run artifacts and distinguish agent failures from infrastructure failures.

Compile the exact host command without spending quota:

```bash
python3 scripts/capture-skill-eval.py skill-eval-job.json --print-command
```

Actual execution requires both `--execute` and `--acknowledge-cost`. Keep it out of ordinary CI.

## Product AI eval loop

```text
change prompt or tool policy
 → run offline fixtures (promptfoo / bank)
 → on fail: fix or deliberate golden update
 → ship only if thresholds hold
 → optional: sample prod traces → new fixtures (redacted)
```

| Rule | Why |
|---|---|
| Goldens are intentional | Silent golden rewrites hide regressions |
| Mock providers in unit CI | Cost + flakiness |
| Redact PII in datasets | Security + compliance |
| Threshold versioned | "Looks fine" is not a gate |

## Maker-checker and evals

Evals are a **checker**. Implementer must not be the only judge of "done":

1. Implementer changes code/prompt.
2. Checker = fixtures + `verify_commands` + optional second agent review.
3. CI is the final checker for skill packages.

See `workflows.md` outer-loop contract.

## Deterministic trajectory state machine

Before adding a hosted trace platform, validate the local execution path against the exact contract:

1. Record ordered sense, plan, action, observation, checkpoint, critique, and stop events.
2. Replay tools, approvals, sinks, transfers, observation evidence/state, planned completion,
   checkpoint freshness, no-progress limits, acceptance coverage, verification, and stop semantics.
3. Keep fixtures offline; add outcome artifacts and independent review before claiming completion.

### Example fixture (shipped)

- Fixture: `templates/fixtures/trajectory-fix-typecheck.json`
- Checker: `scripts/check-trajectory-fixture.py` (offline, no model)

```bash
python3 scripts/check-trajectory-fixture.py \
  --fixture templates/fixtures/trajectory-fix-typecheck.json \
  --trace /tmp/agent-steps.json
```

Trace steps: `{ "tool", "name"?, "ok"?, "exit"? }`. Fixture `edit` matches recorded `edit:path`.

The richer contract path uses:

```bash
python3 scripts/validate-agentic-trajectory.py templates/agentic/trajectory.sample.json \
  --contract templates/agentic/execution-contract.sample.json --json
```

Success requires exactly one final stop plus a checkpoint after the final action and observation.
The checkpoint state must match the latest observed state. A trajectory cannot complete an unplanned
step or omit observation outcome, state, or evidence. Both CLI inputs preserve their supplied file
identity and reject symlinks.

Promote to Harbor/LangSmith when trace volume, exploration, or team review costs more than setup.
Neither local nor hosted traces prove unrecorded behavior is absent or replace end-state graders.

## Comparative optimization receipt

Do not promote a prompt, tool description, model, context policy, loop, or grader from a single
good run. Use the same frozen environment and paired task/trial IDs for baseline and candidate.
Keep capability, regression, holdout, and adversarial tasks disjoint. Gate cost per successful
trial rather than raw cost, and record infrastructure errors separately from agent failures.
Require an independent trace sample so the optimizer is not its only grader.
Bind the receipt to captured trial evidence, derive reported values from that artifact, pair seeds,
counterbalance variant order, blind graders, and keep holdout data evaluation-only. Illustrative
fixtures are never promotion evidence. Captured promotion also runs cryptographic attestation
verification against an exact trusted builder and artifact subject; provenance never replaces
outcome or trajectory grading.

For attributable comparisons, hash the full baseline/candidate configuration bundle and compute
the structural diff. A prompt-version label or two unrelated digests cannot prove that only the
prompt changed.

## Anti-patterns

- Five eval SaaS tools for one app
- Only vibe-checks before merge
- Goldens that encode one model's prose style as law
- Live LLM calls required for unit CI green

## Related

- `ai-boundary.md` - where AI lives in the stack
- `ai-security.md` - redaction and tool risk
- `workflows.md` - eval-regression loop
- `scripts/run-evals.sh` - skill bank harness
- `skill-behavior-evals.md` - live-run evidence and release gates

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
