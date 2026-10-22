# Decision engineering

**Last verified**: 2026-10-22 · **Review cadence**: 6 months (process guidance; recheck the optional Council protocol features first)

Use structured deliberation only for consequential choices with genuine ambiguity: architecture,
security posture, irreversible migrations, agent autonomy, build-versus-buy, major performance
tradeoffs, or conflicting product constraints. A reversible local implementation detail should
use a short decision record, not a panel.

When a decisive fact the decision turns on is uncertain, research or verify it before the decision is
asserted, not after — a load-bearing unknown blocks the call and is resolved, never guessed through.

## Bounded protocol

1. Restate the decision, alternatives, constraints, non-goals, deadline, and evidence already
   available. Stop if participants are solving different problems.
2. Select two to four distinct reasoning methods. Prefer first principles, empirical evidence,
   adversarial risk, system feedback, user impact, or reversibility. Personas alone do not create
   epistemic diversity.
3. Produce independent positions before sharing peer output. If several models or reviewers are
   used, isolate the first pass to reduce anchoring and correlated errors.
4. Anonymize cross-review when identity or provider reputation could bias judgment. Require each
   reviewer to name one specific disagreement, one useful insight, and the evidence that would
   change their position.
5. Run a dissent and counterfactual check. Agreement is not evidence; repeated claims do not gain
   weight without independent support. Preference training partly rewards agreement, and models will
   flip a correct answer under content-free pushback — the sycophancy mechanism and the correction-flip
   evidence are why blind-first positions and this dissent check exist (`epistemic-honesty.md`).
6. Separate empirical, mechanistic, strategic, ethical, and heuristic claims. Link empirical
   claims to sources or repository evidence.
7. Synthesize with a reviewer who did not author a position when practical. Record the decision,
   minority view, acceptable compromises, unresolved questions, confidence, and why simpler
   alternatives lost.
8. End with one owned action and observable kill criteria. If no option clears the declared bar,
   report the split instead of manufacturing consensus.

## Council composition

When `council-of-high-intelligence` is installed and the user requests deeper deliberation, invoke
it as an optional decision engine. Preserve its blind-first analysis, method diversity,
cross-examination, anti-conformity, independent chairman, explicit vote tally, minority report,
kill criteria, and bounded rounds. engineer supplies repository facts, constraints, alternatives,
and verification evidence; Council supplies structured disagreement.

Do not embed historical personas or provider routing inside engineer. This keeps engineer standalone
and prevents ordinary coding work from paying the cost of a full council.

## Failure modes

- Same model repeated under different names.
- Debate before independent analysis, causing anchoring and conformity.
- Majority vote on a factual question that deterministic evidence can answer.
- A chairman who participated and then certifies its own view.
- Forced consensus, confidence without calibration, or no falsification criteria.
- More rounds after the information gain has stopped.
- Deliberation used to defer a decision whose owner and evidence are already clear.

**Related**: `system-architecture.md`, `agentic-engineering.md`, `ai-evals.md`, `workflows.md`

**Research basis**: `../research/anti-slop-and-deliberation-2026-07.md`
