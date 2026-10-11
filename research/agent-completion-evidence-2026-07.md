# Agent completion evidence research

**Date:** 2026-07-15
**Feeds:** `references/prd-to-evidence.md`, `references/agentic-engineering.md`, `scripts/validate-agentic-completion.py`

## Encoded findings

- Completion is a claim about the resulting environment, not the agent's final message or a receipt
  boolean. Bind the claim to the exact contract, trajectory, revisions, scope diff, commands, and
  artifacts that produced it.
- Tests and linters prove only their own assertions. Express each behavioral acceptance criterion as
  explicit JSON-pointer comparisons over captured evidence, then require full criterion coverage.
- Evidence provenance records where, when, and how an artifact was produced. Digests prevent silent
  substitution; independent review checks whether the selected oracle is sufficient for the prose
  criterion and whether the diff stayed in scope.
- A complete decision requires captured rather than illustrative evidence, successful canonical
  contract and trajectory validation, every planned verification command, passing oracles, independent
  review, and no unresolved risk.

## Primary sources

- SLSA, [Provenance](https://slsa.dev/spec/v1.2/provenance)
- NIST, [AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

## Limits

The receipt validates local evidence structure, hashes, command records, and deterministic oracles. It
does not prove that the command recorder is honest, the test is free of blind spots, or the oracle fully
captures the user's intent. High-impact work still needs independent oracle-sufficiency and scope review;
reviewer labels are not authenticated. Signed CI attestations or trusted runner and reviewer provenance
can strengthen the capture chain.
