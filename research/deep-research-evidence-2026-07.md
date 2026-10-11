# Deep-research evidence integrity

**Reviewed**: 2026-07-15

## Gap

Field completeness is necessary but weak. A result can fill every field while citing one unrelated
page, using stale facts, hiding inference as fact, or presenting a fluent synthesis whose sources do
not support its claims. Report generation previously trusted structurally valid item JSON.

## Decision

Engineering presets now opt into `claim_v1`. Each result carries a dated evidence bundle:

- typed source entities with stable IDs, canonical HTTPS URLs, publisher, access date, and optional
  publication date or immutable revision;
- typed atomic claims mapped to one schema field and one or more source IDs;
- explicit fact, inference, or comparison kind plus bounded confidence;
- exact claim coverage for required non-identity fields unless the field is declared uncertain.

The offline validator catches graph and chronology defects. It does not fetch pages or judge whether
the cited text semantically entails the claim. That requires a tool-capable evidence review. Report
generation replays the validator so the publishing path cannot bypass the contract.

Topic validation adds the comparison boundary. It binds publication to the approved outline set,
rejects missing, extra, or duplicate result identities, confines result files below the topic root,
requires one research cutoff across `claim_v1` items, and rejects conflicting identity metadata for
the same source URL. This prevents a complete-looking report from comparing different candidate sets
or temporal snapshots without disclosure.

Claim-support review adds the semantic audit boundary. Presets require a distinct reviewer to inspect
the cited material, capture the smallest sufficient evidence excerpts, and grade every current claim
as supported, partial, unsupported, or unverifiable. A receipt binds the outline, field contract,
result files, claim statements, cited source identities, and captured excerpts by SHA-256. Required
reviews publish only when every claim is supported and approved; stale inputs, missing claims,
evidence tampering, source mismatch, or self-review fail.

A follow-up patch audit found that semantic validation initially assumed the default `results/`
directory even though the outline supports a custom `execution.output_dir`. Validation now derives
the configured strict descendant consistently across initialization, topic checks, semantic review,
and report generation. It also requires the captured evidence source set to equal, rather than only
contain, each claim's cited source set.

This is deliberately narrower than an automated truth claim. It proves what local bytes a declared
reviewer assessed and preserves explicit verdicts. It does not attest that excerpts faithfully
represent remote sources, that reviewer identities are genuine, that retrieval was exhaustive or
unbiased, that measurement methods are comparable, or that claims are true beyond the captured
evidence.

## Research basis

- W3C PROV models entities, activities, agents, derivation, attribution, and primary-source links.
  Engineer uses a smaller JSON projection appropriate for item research rather than RDF.
- DeepResearch Bench separates report quality from retrieval quality and evaluates effective citation
  count and citation accuracy.
- DRACO evaluates accuracy, completeness, objectivity, and citation quality as separate dimensions.
- DREAM warns that fluent, citation-aligned synthesis can still obscure factual and temporal errors;
  it argues that temporal and factual evaluation needs tool parity rather than static inspection alone.
- NIST AI RMF emphasizes documented limits, measurement, scientific integrity, and test/evaluation/
  verification/validation rather than treating generated output as self-authenticating.
- Deep Research Bench II uses atomic, verifiable rubrics produced through an expert-reviewed pipeline
  and reports that leading systems still satisfy fewer than half of them.
- ReportLogic separates macro, expositional, and structural claim-support logic and finds that generic
  LLM judges can be influenced by verbosity and other superficial cues.
- Grounded-claim factuality work frames support checking as constrained reading comprehension rather
  than unconstrained fluent critique.

## Primary sources

- https://www.w3.org/TR/prov-o/
- https://arxiv.org/abs/2506.11763
- https://arxiv.org/abs/2602.11685
- https://arxiv.org/abs/2602.18940
- https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
- https://arxiv.org/abs/2601.08536
- https://aclanthology.org/2026.acl-long.384/
- https://aclanthology.org/2026.acl-long.1468/
