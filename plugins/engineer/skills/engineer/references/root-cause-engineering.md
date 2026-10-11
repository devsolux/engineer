# Root-cause engineering: fix the cause, not the symptom

**Last verified**: 2026-07-16 · **Review cadence**: 3 months
**Related**: `system-assurance.md`, `coding-principles.md`, `refactoring.md`,
`implementation-completeness.md`, `agent-incident-response.md`

Use this module for every bug fix, hotfix, workaround request, "quick fix," or recurring
incident. A fix is a repair of the first causal divergence from a stated invariant, verified
at the layer where the divergence occurred. Anything else is a mitigation and must say so.

## Diagnosis contract (before any patch)

Run the systematic debug loop in `system-assurance.md` (reproduce → trace the real path →
first divergence). Do not duplicate it; this contract adds the fix-side obligations:

1. **Reproduce first.** A failure that cannot be reproduced or deterministically observed
   cannot be declared fixed. If reproduction is impossible, instrument the blind spot and
   report the fix as unverified.
2. **State the violated invariant.** Name the rule, contract, or expected transition that
   broke, not just the visible error message.
3. **Build the causal chain.** Walk from symptom back through the real execution path until
   the first point where behavior diverged from the invariant. That divergence is the fix
   site; everything downstream is a symptom.
4. **Bounded five-whys.** Ask "why" until the answer is either (a) a defect you can repair in
   scope, (b) a structural cause that routes to `refactoring.md`, or (c) a cause outside
   current authority (vendor, platform, upstream team) that must be escalated and declared.
   Stop there; do not manufacture ever-deeper causes past the actionable boundary.
5. **Confirm the mechanism.** The patch must explain the observed failure. If the fix works
   but you cannot say why the bug happened, the diagnosis is incomplete - keep digging or
   report the uncertainty explicitly.

## Symptom-patch prohibition

A patch that makes the symptom disappear while leaving the causal defect in place is a
**defect, not a fix** - it converts a visible failure into a hidden one plus permanent
complexity. Characteristic offenders:

| Symptom patch | What it hides | Root-cause question |
|---|---|---|
| Retry loop around a flaky call | Race condition, missing idempotency, ordering bug | Why does the call fail nondeterministically? |
| Null/undefined guard at the crash site | Broken invariant upstream that produced the null | Which producer violated the "never null here" contract? |
| Widened timeout / raised limit | N+1 query, unbounded payload, missing index | Why did latency grow past the old budget? |
| Catch-and-continue / swallowed error | Real failure now invisible to callers and telemetry | What should fail loudly, and where? |
| Restart/cron "self-heal" | Resource leak, unbounded growth, poisoned state | What accumulates between restarts? |
| Test/fixture/assertion edit to go green | The defect itself | (Forbidden - see `implementation-completeness.md`) |
| Feature flag or config toggle "off" | Unfixed path still shipping | When does the path come back, owned by whom? |

Each of these may be legitimate **engineering** (retries with idempotency, defensive
boundaries, tuned budgets) when designed deliberately - but never as the *response to a
diagnosed defect* whose cause remains in place.

## Declared-mitigation exception protocol

A symptom-level mitigation may ship only as a **declared temporary measure**, never silently.
Legitimate triggers: active incident pressure, cause outside current authority, or a
root-cause repair too large for the current change window. The declaration requires all of:

- **Label** - the change is named a mitigation in the code comment, commit/PR, and report;
  it is never described as the fix.
- **Owner** - a named person or role accountable for the follow-up.
- **Expiry** - a date or release by which the mitigation is removed or re-justified.
- **Tracked follow-up** - a filed issue/task for the root-cause repair, linked from the
  mitigation site, with the diagnosis evidence attached.
- **Detection** - a signal (alert, metric, failing check) that fires if the underlying defect
  worsens while masked.

A mitigation without all five is a symptom patch and fails review.

## Fix-time architecture gates

Before committing a fix, evaluate it against the structural gates in `coding-principles.md`
(SOLID-as-diagnostic table and proportionality gate):

- **Coupling** - does the fix add a dependency, shared state, or cross-boundary reach that
  did not exist before? A fix that increases coupling to silence a symptom is structural debt.
- **Invariant boundary** - does the fix respect the layer that owns the invariant, or does it
  re-check/duplicate the rule somewhere it does not belong?
- **10x question** - does the repair still hold at 10x load, data volume, or concurrency, or
  does it only move the threshold at which the same failure returns?
- **Proportionality** - do not over-engineer the fix either; no new abstraction, service, or
  framework without the evidence the proportionality gate demands.

## Minimal diff, applied at the cause

The minimal-diff rule (`coding-principles.md`) means the smallest change **at the causal
site** - not the smallest change anywhere that hides the symptom. A one-line guard at the
crash site is often larger in true cost than a five-line repair of the producer.

When diagnosis shows the origin is structural (god module, duplicated rule, missing
boundary), route into the `refactoring.md` safety loop as a **preceding step**: green
baseline → behavior-preserving restructure → then the now-small causal fix. Do not blend
feature, refactor, and fix into one diff.

Always add the smallest failing regression test at the lowest sufficient layer before the
repair, and watch it fail for the diagnosed reason (`system-assurance.md` step 5).

## Completion language

Report the two states distinctly; they are not interchangeable:

- **"Root-cause fixed"** - first causal divergence repaired, regression test failed-then-passed
  for the diagnosed reason, verification run at the failing layer.
- **"Mitigated"** - symptom suppressed under the declared-mitigation protocol; owner, expiry,
  tracked follow-up, and detection signal stated in the report.

Never report a mitigation, an unreproduced fix, or an unexplained recovery as "fixed."

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
