# Academic research skill comparison

**Date**: 2026-07-16
**Candidate**: `Imbad0202/academic-research-skills`
**Pinned revision**: `d8c0f43304b00682961db33812ebd208096a28d8`
**Disposition**: research input only; do not install or copy

## Supply-chain result

The inspected revision is a large Claude-oriented academic research and publication suite. It includes multiple skills, agents, hooks, Python tools, external scholarly API adapters, hundreds of fixtures, and optional cross-model execution. The commit is GitHub-verified. The repository uses CC BY-NC 4.0, which is not a suitable dependency for silently incorporating material into Engineer's separately licensed and potentially commercial workflows. Popularity, a verified commit, and extensive tests do not establish safe runtime behavior.

No candidate code or prose was copied. The review extracted workflow ideas and re-specified them independently for Engineer's engineering-research context.

## Comparative decision

Engineer already has stronger controls for its core job in several areas:

- exact outline-to-result coverage and a single cutoff;
- confined regular files and symlink rejection;
- claim-level sources plus hash-bound captured excerpts;
- independent semantic review and fail-closed publication;
- source-identity consistency across compared items;
- explicit separation between structural validity and truth.

The candidate is materially deeper in academic-specific work: research-question formation, systematic reviews, PRISMA, discipline-relative evidence grading, citation-version families, temporal reasoning, contradiction tracking, research failure modes, reviewer calibration, and degraded-mode inventories. Academic paper writing, peer review simulation, citation formatting, IRB/preregistration, and meta-analysis should remain a separate specialist capability rather than inflate Engineer.

## Patterns adopted

1. **Research charter before outline**: freeze the decision, research question, scope, exclusions, negative constraints, cutoff, evidence standard, source access, and stop conditions.
2. **Claim-relative source fitness**: official documentation is strongest for current product behavior; experimental, observational, qualitative, archival, legal, and consensus claims need evidence appropriate to the claim and field. One universal evidence pyramid is unsafe.
3. **Coverage and contradiction ledger**: record searched concepts, synonyms, source classes, missing regions or perspectives, negative results, contrary evidence, and unresolved gaps. Never call an ordinary search exhaustive.
4. **Time and version integrity**: bind claims to the exact source edition or revision; prevent mixed metadata and quotations, future-as-past errors, causal inversion, unmaterialized comparators, and unstable words such as "currently" without an as-of date.
5. **Integrity sweep**: check fabricated or mismatched citations, invented methods or results, shortcut reliance, selective evidence, unsupported conclusions, frame lock, and errors reframed as discoveries.
6. **Degradation register**: record unavailable APIs, inaccessible sources, missing reviewers, truncated evidence, changed behavior, downstream effect, and terminal policy. Missing evidence is not equivalent to a clean check.
7. **Reviewer calibration**: before a model-based semantic reviewer becomes a hard gate, measure it on representative supported, partial, unsupported, ambiguous, and unavailable cases; report class-level errors and keep the gate advisory until performance is adequate for the target domain.

## Patterns rejected or kept separate

- Do not install the candidate, its hooks, or its API clients into trusted Engineer hosts from this review.
- Do not copy a 13-agent or 10-stage academic pipeline into routine engineering research.
- Do not treat reviewer panels, score trajectories, or model tiering as proof of correctness.
- Do not claim systematic review, meta-analysis, exhaustive search, or PRISMA compliance without a registered protocol, reproducible search strings, databases, dates, screening decisions, deduplication, risk-of-bias method, and flow counts.
- Keep academic authorship, journal submission, citation formatting, human-subjects research, and statistical synthesis with a separately admitted specialist skill.

## Source

- Repository: https://github.com/Imbad0202/academic-research-skills
- Pinned tree: https://github.com/Imbad0202/academic-research-skills/tree/d8c0f43304b00682961db33812ebd208096a28d8
- License: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/LICENSE
- Architecture: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/docs/ARCHITECTURE.md
- Deep research skill: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/deep-research/SKILL.md
- Research failure modes: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/academic-pipeline/references/ai_research_failure_modes.md
- Reviewer calibration: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/academic-pipeline/references/claim_audit_calibration_protocol.md
- Temporal verification: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/docs/design/2026-05-18-ars-v3.9.4-temporal-verification-spec.md
- Version-family reconciliation: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/docs/design/2026-05-28-kong-258-version-family-reconciliation.md
- Degradation registry: https://github.com/Imbad0202/academic-research-skills/blob/d8c0f43304b00682961db33812ebd208096a28d8/docs/design/2026-07-15-511-degradation-registry-design.md
