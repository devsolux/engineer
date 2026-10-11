# Behavioral skill evaluations

**Last verified**: 2026-07-16 · **Review cadence**: 3 months

Use this module when a skill change needs evidence that a real agent followed the skill. Static
bank validation remains useful, but it is specification lint, not a behavioral result.

## Contents
- [Evidence stack](#evidence-stack)
- [Integrity rules](#integrity-rules)
- [Deterministic grading and paired comparison](#deterministic-grading-and-paired-comparison)
- [Behavioral-run artifact](#behavioral-run-artifact)
- [Cross-host capture](#cross-host-capture)
- [External runner threshold](#external-runner-threshold)

## Evidence stack

1. Freeze the skill version and hashes for the skill, prompt bank, host instructions, tools, and
   repository fixture.
2. Select capability, regression, private holdout, and adversarial cases without showing hidden
   expectations to the tested agent.
3. Run repeated trials in resettable fixtures. Capture output, tool trace, resulting state, usage,
   latency, and error class.
4. Apply deterministic outcome graders first, then trajectory graders. Use model graders only for
   judgment that cannot be expressed as code.
5. Human-review a stratified sample of passes, failures, boundary scores, and every proposed
   promotion's safety failures. Calibrate each model-grader version against that sample.
6. Compare the candidate with a frozen baseline. Promotion must protect regression, holdout,
   safety, cost, latency, and infrastructure-error budgets.

## Integrity rules

- Keep `agent_failure` separate from `infrastructure_error`; report both denominators.
- Store artifact paths and SHA-256 hashes. Failed trials are evidence and must be retained.
- Outcome grading must inspect resulting state where the task mutates files, data, or browser state.
- A successful agentic trial needs at least one outcome grader and one trajectory grader.
- The tested agent cannot also be the independent reviewer or grader author for promotion evidence.
- Model graders need a named rubric, version, evidence references, and human calibration.
- Public scenarios can be smoke tests, but a promotion decision requires uncontaminated private
  holdout or newly sampled cases.
- Capture jobs select a prompt by ID from a hash-bound dataset. They never carry a free-form prompt,
  expected output, assertion, rubric, grader, or promotion label.
- Report uncertainty and per-case results. Never hide regressions behind an aggregate mean.

## Deterministic grading and paired comparison

Keep oracles outside the runtime bundle and tested-agent context. Build from
`templates/agentic/skill-eval-oracle.sample.json`; use literal or structured trace checks for facts
that can be expressed without model judgment. Each oracle must cover outcome and trajectory, and may
add safety checks. Only grade a capture that passes canonical validation:

```bash
python3 scripts/grade-skill-eval-capture.py capture.json \
  --oracle private/oracle.json --root . --output grade.json
python3 scripts/validate-skill-eval-grade.py grade.json --root .
```

The receipt binds the capture, oracle, runtime version, and artifact hashes. Validation replays the
grader instead of trusting stored booleans. A single grade is never promotion evidence.

Evidence publication is immutable by default. Grade and comparison outputs use exclusive creation,
so an existing file or final symlink fails instead of being replaced. Host-capability receipts use
the same primitive. MCP transcript compilation requires a new output directory and exclusively
creates every package member. This prevents accidental evidence history rewrites and closes the
common pre-planted-name symlink race; it does not claim control over an arbitrary parent directory
chosen outside a repository trust root. Telemetry is different: it is a validated append-only ledger
and keeps its own identity, locking, and append contract. The recorder holds a sibling Unix advisory
lock across existing-ledger validation, duplicate detection, append, `fsync`, and post-validation.
It opens the ledger with append and no-follow flags where available, compares device and inode before
writing, and rolls back its appended bytes if canonical validation fails. The lock coordinates Engineer
recorders; it does not stop a process that ignores advisory locking.

Bind every oracle to an explicit trial ID and seed. Paired trials require a comparison plan from
`templates/agentic/skill-eval-comparison.sample.json`. Baseline and candidate must have identical
host/model/scenario/trial coverage and identical seeds. Compile the
report with:

```bash
python3 scripts/compare-skill-eval-grades.py comparison.json --root . --output report.json
python3 scripts/validate-skill-eval-comparison.py report.json --root .
```

The report includes per-trial regressions, safety regressions, Wilson 95% intervals, coverage, and
machine-readable gates. Promotion fails closed unless evidence is captured, variants are distinct,
the dataset is private or sequestered holdout, minimum scenario/repetition coverage is met, and pass
and safety budgets hold. Cost and latency remain separate gates in the full behavioral-run receipt
until capture receipts expose trustworthy host-neutral usage fields.

## Behavioral-run artifact

Use `templates/agentic/skill-eval-run.sample.json` and validate it with:

```bash
python3 scripts/validate-skill-eval-run.py skill-eval-run.json --json
```

The validator checks provenance, repository file hashes, coverage, layered graders, independence,
calibration, error accounting, paired baseline metrics, and release-decision consistency. It validates captured evidence; it does not
launch a model or claim that a static scenario bank was executed.

The shipped sample is marked `illustrative_fixture`. Copying or expanding it cannot authorize a
promotion; only a `captured_run` produced by an actual isolated execution can be eligible.

## Cross-host capture

Open `templates/agentic/skill-eval-job.sample.json`. First inspect the compiled command:

```bash
python3 scripts/capture-skill-eval.py skill-eval-job.json --print-command
```

The schema-v5 job must bind a canonically validated host inventory, selected host, executable,
version-output and help-output hashes, plus the sorted capabilities required by its adapter. A real
run, bind a `captured_inventory`, not the illustrative sample. Immediately before any paid execution,
the launcher captures the live host again and rejects executable, version surface, help surface, or
required-capability drift. The resulting capture manifest records that revalidation. Its evidence
reviewed local CLI identity and advertised surface; it still does not prove effective managed policy,
sandbox implementation, network enforcement, credential scope, or provider behavior.

Adapter capability lists are exact policy, not caller-selected subsets. The Codex adapter requires
`--strict-config` and compiles it with `--ignore-user-config`; an unknown or stale config override must
fail before model launch. Removing a required capability from an old job invalidates the job even when
the remaining capabilities appear in local help output.

Review the same preflight without spending quota:

```bash
python3 scripts/capture-skill-eval.py skill-eval-job.json --verify-live-host
```

The job also binds a deterministic engineer runtime bundle by SHA-256. The allowlist includes the skill
entrypoint and runtime modules, while hidden evals, research, capture machinery, fixture answers, git
state, and local plans are excluded. Symlinks fail closed. The runner copies that exact package into a
disposable host-native location and verifies its digest again after copying; an isolated host cannot
silently run without engineer and still produce valid capture evidence.

The compiler supports Codex and Claude adapters. It requires a marked repository fixture, denied
network, no external writes, bounded time/turns/cost, a capture directory under
`.engineer/eval-captures`, and a hash-bound scenario source. It rejects jobs containing hidden-answer
keys. Illustrative jobs cannot execute.

After reviewing a `captured_run` job, execution is deliberately two-key:

```bash
python3 scripts/capture-skill-eval.py skill-eval-job.json --execute --acknowledge-cost
```

Never put this paid execution path in default CI. Keep raw JSONL, stderr, and final output. Then grade
them afterward and compile the result into the behavioral-run receipt; capture success alone is
not task success.

Captured execution uses direct API-key automation only: `CODEX_API_KEY` for Codex or
`ANTHROPIC_API_KEY` for Claude. The launcher creates a disposable HOME and isolated `CODEX_HOME` or
`CLAUDE_CONFIG_DIR`, never passes the real home/config location, cached OAuth state, keyring access,
other provider credentials, or unrelated environment values, and deletes the temporary home after the
process exits. Codex also keeps `shell_environment_policy.inherit=none`, disables cached web
search explicitly, and installs the bundle at `$CODEX_HOME/skills/engineer`. Claude bare mode skips
keychain reads. Missing API-key auth fails before model launch. The provider process necessarily receives
its own API key; use a short-lived, least-privilege project key and external runner isolation for stronger
credential guarantees.

Claude jobs expose exactly Read, Glob, and Grep as logical tools, but the CLI must not receive bare
`Read`, `Glob`, or `Grep` allow rules. Bare `Read` means all file reads. The adapter instead grants
`Read(./**)`; Claude applies Read rules best-effort to Glob and Grep, checks both symlink and resolved
target, and `dontAsk` denies access that is not pre-approved. Bash, Edit, Write, web tools, Agent, and
NotebookEdit are denied. The only explicit plugin is a temporary `engineer-eval` package invoked as
`/engineer-eval:engineer`; hooks, auto-memory, unrelated plugins, MCP discovery, keychain reads, and session
persistence remain absent under the bare adapter. It is a host-enforced tool boundary,
not an OS filesystem sandbox; use an external container/VM for higher-assurance hostile fixtures.

All hash-bound job, capture, artifact, oracle, grade, comparison, optimization, telemetry-source,
and browser-lane paths use one lexical confinement primitive. Reject `..`, absolute references,
root escape, and a symlink in any supplied component before resolving or hashing the target. A hash
that matches through an in-repository alias does not turn that alias into a regular evidence file.

## External runner threshold

Do not add a container merely to make a read-only routing smoke look sophisticated. Require an external
runner for hostile repositories, executable fixtures, untrusted archives, or stronger credential/network
claims. The reviewed runner contract must prove: disposable image identity; read-only fixture and skill
mounts; tmpfs HOME; no host sockets or developer config; denied egress except the selected provider;
short-lived provider key; PID/CPU/memory/time/cost limits; non-root process; artifact export allowlist;
cleanup; and a runner receipt independent of the model. A Compose file alone proves none of these.

Provider-executed baselines remain manual because they spend quota and require private holdouts. Before
the first paid run, capture current host inventory, create one reviewed `captured_run` job per host, run
the live preflight, execute with explicit cost acknowledgement, validate and secret-scan artifacts, then
derive local telemetry and grade with the frozen host-neutral oracle. Never put provider calls in default
CI or commit private holdouts/raw traces.

Prepare public smoke jobs without execution or quota spend:

```bash
python3 scripts/prepare-skill-eval-baseline.py --scenarios 121 --hosts codex,claude --activation-modes explicit,implicit
```

The generator captures and validates live host evidence, compiles the complete batch before publishing
it, reports only API-key presence, and writes ignored artifacts beneath `.engineer/eval-jobs/`. An
exclusive lock rejects concurrent preparation. Secure temporary files and same-directory replacement
publish each file, while `manifest.json` is written last as the batch commit marker. A failed arm leaves
no valid manifest, so loose job files are never execution-ready evidence.

Validate the commit marker before reviewing or executing any job:

```bash
python3 scripts/validate-skill-eval-batch.py .engineer/eval-jobs/manifest.json --root .
```

The validator replays every canonical job, verifies hashes and batch bindings, and requires exact
host by scenario by activation-mode coverage. Replays accept identical jobs and reject non-identical
collisions. Per-file replacement is atomic; the directory is not a filesystem-wide transaction. Review
every job before using `--execute --acknowledge-cost`; private holdout prompts remain outside git.

The generator produces a paired explicit control and keyword-free implicit arm by default. Both append
the neutral `[routing-probe:alpha]` request, but only the exact reviewed Engineer body contains the
required response marker. An implicit arm contains no `$engineer`, `/engineer`, or equivalent invocation.
The marker must occur exactly once in final output or capture fails. A valid occurrence proves the reviewed body was
loaded under the local compiler contract; it does not prove provider honesty, instruction compliance
beyond the marker, or task quality. Evaluate task behavior separately and compare paired arms.

The launcher emits a schema-v5 `capture.json` and immediately invokes
`validate-skill-eval-capture.py`. That validator binds the exact job, host evidence, execution result,
the supplied skill bundle, and output/trace/log paths, sizes, and hashes; caps each artifact at 10 MB; and blocks high-confidence
credential patterns. It requires `behavioral_pass: null` and `grading_required: true`, so an exit-zero
capture cannot self-promote. Preserve a rejected artifact securely for incident review, but never pass
it to graders or reports until secrets are revoked and the evidence is sanitized and recaptured.

The skill binding also records explicit/implicit mode, exact invocation (null for implicit), sealed
probe digest and confirmation, and host-native registration mechanism. After the
run, known unresolved-skill or unknown-command markers in final output, trace, or stderr force capture
failure even when the process exits zero. Absence of those markers proves only that no known resolution
failure was observed; it is not independent proof that the provider expanded or followed the skill.

Schema v5 also separates a repository-root-normalized, reconstructable `logical_command_sha256` from the observed
`executed_argv_sha256`. The validator runs the bound job through the canonical compiler and rebuilds
the logical command using the captured output path. Root normalization keeps identical reviewed jobs
portable across checkout paths. A matching digest proves agreement with the local
compiler and reviewed job; the executed-argv digest remains an observed record unless a trusted runner
attests it.

Harness-lever tuning (tool schemas, deferred loading, routing) reuses this discipline with paired
baseline arms and pass@N for nondeterministic routing: `prompt-optimization.md` harness levers.

**Related**: `ai-evals.md`, `prompt-optimization.md`, `agentic-engineering.md`

**Research basis**: `../research/behavioral-skill-evals-2026-07.md`
