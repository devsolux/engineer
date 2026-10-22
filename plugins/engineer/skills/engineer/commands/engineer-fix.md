---
description: Audit then repair — minimal diff fixes for engineer violations in the target scope.
argument-hint: "<target> [--findings <run>/findings.json]"
---

# /engineer-fix

Load engineer `SKILL.md` + `references/root-cause-engineering.md`. Mode: **diagnose → audit → fix in atomic steps**.

Target and symptom follow this invocation. With `--findings <run>/findings.json` the input is a
security-audit receipt instead: follow **Findings mode** below and also load the "From findings
to fixes" section of `references/security-audit.md`.

## Execute

1. **Diagnose** — reproduce, state the violated invariant, trace the causal chain to the
   first divergence (`references/root-cause-engineering.md` + system-assurance debug loop).
2. **Mini-audit** — list Critical/Warning for scope only (brief).
3. **Fix** — one issue at a time, minimal diff **at the causal site**, match repo conventions.
4. **Verify** after each batch:
   ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
   npm run typecheck
   bash "$ENGINEER/scripts/engineer-scan.sh" --strict
   ```
5. **Report** — what changed, what remains; say "root-cause fixed" or "mitigated" explicitly.

## Findings mode (`--findings`)

The audit already diagnosed each record: `boundary` is the violated invariant, `trace` the causal
chain, `root_cause` the first divergence, `remediation` the layer and paths to repair.

1. **Validate first** — never fix from a receipt that fails; report its errors and stop:
   ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
   RUN=.engineer/security-audit/run-001
   python3 "$ENGINEER/scripts/validate-security-findings.py" "$RUN/findings.json" --evidence-root "$RUN" --target-root .
   ```
2. **Partition by verdict** — the verdict decides, never the user's confidence in a record:
   - `confirmed` → the fix queue, by `severity.overall` (critical → low), ties by fingerprint.
   - `needs_validation` → never patched. Run its `validation_plan.local` steps (inside an
     OS-enforced sandbox whenever `sandbox_required` is true) and record which expected outcome
     occurred; without that sandbox, and for `owner_observed` steps, hand the steps to the user
     verbatim. A result matching
     `expected_if_vulnerable` goes back to `/engineer-security-audit` for re-verification into a
     `confirmed` record with a remediation; it is fixed in a later pass, not this one.
   - `rejected` → skipped; list each fingerprint with its `rejection.reason`.
3. **One confirmed record per atomic change**, in queue order:
   - Re-read every trace path; if the code no longer matches the trace, stop and send the
     record back for re-verification.
   - Write the regression test first, at the lowest layer that crosses the boundary: drive the
     trace's `entrypoint` with the boundary's `input` as a synthetic `principal` and assert the
     `result` does not occur (name it after `remediation.regression_test` when set). Watch it
     fail for the diagnosed reason.
   - Repair at `remediation.layer`, editing only `remediation.paths` plus the test. Needing any
     other source file means the record is wrong: stop and re-verify it; never widen scope.
   - Watch the test pass, then run step 4 of Execute and the target's test suite.
4. **Receipt** — write `$RUN/remediation.json` (shape:
   `templates/agentic/security-remediation.sample.json`): one entry per fixed record, every
   other record under `not_fixed` as `deferred` (confirmed, with a reason), `handed_back`, or
   `skipped`. Then cross-check it:
   ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
   python3 "$ENGINEER/scripts/validate-security-findings.py" "$RUN/findings.json" --evidence-root "$RUN" \
     --target-root . --remediated "$RUN/remediation.json"
   ```
5. **Report** per fingerprint: root-cause fixed, mitigated, or deferred, with the test and the
   verification commands; then the handed-back steps and the skipped list. A fingerprint counts
   as fixed only after the next audit run re-verifies it (carry-forward rule).

## Rules

- Root cause is a diagnosis obligation, not just a scope limiter — no patch before the first causal divergence is identified
- No silent symptom patches (retry masking a race, null guard hiding a broken invariant, widened timeout hiding an N+1); mitigations ship only declared, with owner + expiry + tracked follow-up
- No drive-by refactors; structural causes route through `references/refactoring.md` first as a separate step
- Do NOT touch files outside stated scope
- Auth bugs → `backend-auth.md`; colors → `design-system.md`; RLS → `backend-database.md`
- Findings mode never edits `findings.json` or other audit artifacts; it writes only `remediation.json`

## Loop

For repeated verify until green: `/engineer-loop-verify` (uses `/loop` skill)
