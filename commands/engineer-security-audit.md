---
description: Hunt and verify real vulnerabilities in a codebase with a coverage ledger, refutation, and evidence verdicts — report only.
argument-hint: "<path|repo> [--profile quick|standard|deep] [--scope …] [--out DIR]"
---

# /engineer-security-audit

Load `references/security-audit.md`. Hunters and verifiers load
`references/security-attack-classes.md` and the matching domain section of
`references/security-audit-domains.md` per wave; the parent does not preload them.

Confirm `$ARGUMENTS` names a codebase the user owns or is explicitly authorized to audit.
Guidance mode is the default: answer a focused security question from the modules without run
artifacts. Enter full audit mode only on an explicit request to audit the codebase, find
vulnerabilities, run a pen-test-style source review, or produce the findings artifact. When the
request is ambiguous, ask one focused question: a full audit run with `findings.json` and a
report, or guidance on a specific concern?

Full audit mode writes to the next `.engineer/security-audit/run-<NNN>/` under the target, or to
`--out DIR` when the target is mounted read-only. Findings are sensitive: `.engineer/` must be
gitignored in the target, and run artifacts are never committed or pushed. `--profile` sets
breadth (quick, standard, deep), never the evidence bar; `--scope` narrows the surfaces.

1. **Reconnaissance** (`security-audit.md`): read every prior `run-*/coverage.json` and
   `findings.json`, write `architecture.md` (at most 1000 words, eight headings), declare
   surfaces, boundaries, subsystems, and attack classes, and reserve budget for critics and
   verification before any hunting. Initialize the ledger with `security-ledger.py init`.
2. **Hunting waves** (`templates/agentic/prompts/security-hunter.md`): assign planned ledger
   units to isolated hunters that load `security-attack-classes.md` plus the matching domain
   section. Each hunter returns one JSON result in its own scratch; promote it with
   `security-ledger.py promote` after the regular-file, size, JSON, and assigned-unit checks.
3. **Coverage critic** (`templates/agentic/prompts/security-coverage-critic.md`): after each
   wave, a fresh critic that did not hunt reviews the brief and ledger for missing units, units
   to reassign, and prior-run leads. Hunting continues until the critic returns `stop`.
4. **Refutation** (`templates/agentic/prompts/security-verifier.md`): every unique candidate
   fingerprint goes to a verifier that did not hunt it. The verifier tries to refute first and
   returns `confirmed`, `needs_validation`, or `rejected` with the complete record.
5. **Record review** (`templates/agentic/prompts/security-record-reviewer.md`): an independent
   reviewer checks each record. A material replacement goes to another verifier independent of
   the hunter, the verifier, and the reviewer. Write `findings.json` with exactly those three
   verdicts and validate it.
6. **Report** (`security-audit.md`): write `REPORT.md`, `FINDINGS-DETAIL.md`, and
   `NEEDS-VALIDATION.md`, target-neutral, with the sandbox statement, the run status and its
   exact incomplete reason, and the units left uncovered. A clean run reports zero findings and
   says so.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
RUN=.engineer/security-audit/run-001   # dimensions.json and architecture.md written by reconnaissance
python3 "$ENGINEER/scripts/security-ledger.py" init --dimensions "$RUN/dimensions.json" --run-id run-001 \
  --target-name app --source-ref "$(git rev-parse HEAD)" --architecture architecture.md --output "$RUN/coverage.json"
python3 "$ENGINEER/scripts/security-ledger.py" assign "$RUN/coverage.json" --wave 1 --hunter hunter-a --critic critic-1 cov-<12 hex>...
python3 "$ENGINEER/scripts/security-ledger.py" promote "$RUN/coverage.json" "$SCRATCH/hunter-a/result.json" --agent hunter-a --wave 1
python3 "$ENGINEER/scripts/security-ledger.py" gap "$RUN/coverage.json" --prior .engineer/security-audit/run-000   # when a prior run exists
python3 "$ENGINEER/scripts/security-ledger.py" finish "$RUN/coverage.json"   # or --incomplete "<exact reason>"
python3 "$ENGINEER/scripts/validate-security-coverage.py" "$RUN/coverage.json" --evidence-root "$RUN" --json
python3 "$ENGINEER/scripts/validate-security-findings.py" "$RUN/findings.json" --evidence-root "$RUN" --json
```

Never edit target source; only the parent writes run artifacts, and agents write their own
scratch only. Never execute target code outside an OS-enforced sandbox with no network, an empty
allowlisted environment, a read-only target and toolchain, scratch-only writes, and CPU, memory,
and wall limits; without one, do not execute and record a `needs_validation` blocker. Never probe
live, shared, staging, or production systems; principals and secrets are synthetic. Severity
appears only on `confirmed` records and never exceeds the demonstrated impact. Validators prove
record consistency and evidence binding, never exploitability or the absence of vulnerabilities.
Fix, install, enable, and deploy decisions stay separately authorized; hand remediation to
`/engineer-fix --findings "$RUN/findings.json"` only on an explicit request.
