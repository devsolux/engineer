# Optimization runtime identity binding - 2026-07

## Finding

The earlier attribution contract proved that the recorded baseline and candidate differ at exactly one declared JSON pointer,
but the trial artifact named only `baseline` and `candidate`. A correctly hashed artifact could
therefore be attached to a different variant bundle unless the signed experiment binding and a
semantic validator jointly bound those labels to exact configuration identities.

## Implemented contract

- Canonical JSON SHA-256 for each complete variant, including its version.
- Canonical SHA-256 for prompt, context, tool, loop, model, grader, and environment separately.
- Exact baseline/candidate binding set in trial-artifact schema v2.
- Validator-derived comparison; the evidence producer cannot select which fields are checked.
- Negative fixtures for swapping, omission, insertion, forgery, and stale bindings.

The signed experiment binding already includes the variant-bundle path and file digest. The new
semantic layer proves which configuration each trial label means. It still cannot prove that an
opaque provider honored every requested parameter. Provider request IDs, retained redacted
request/response envelopes, or a trusted harness attestation are the next trust boundary.

## Sources

- OpenAI eval guidance: pin evaluated behavior and preserve run evidence rather than relying on a prompt label.
- SLSA provenance model: identify exact subjects and build inputs, then verify them against external policy.
- NIST agentic evaluation guidance: retain machine-readable audit trails and evaluate system behavior at the action boundary.
