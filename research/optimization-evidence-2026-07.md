# Evidence-bound prompt and loop optimization

**Date:** 2026-07-15

## Question

What must engineer retain before it can claim that a prompt, context, tool, loop, model,
grader, or environment change improved an agent system?

## Findings

1. Aggregate scores are not sufficient evidence. NIST AI 800-3 distinguishes performance
   on a fixed benchmark from generalization to a broader task population and recommends
   making the statistical assumptions and measurement target explicit. Repeated trials can
   improve precision, but they do not repair a contaminated or poorly defined estimand.
2. Agent evaluation needs a machine-readable audit trail. NIST's agentic evaluation-probe
   program records structured evidence that maps outputs and decisions to the material used
   to check them. A receipt that merely repeats a score is not such a trail.
3. Evaluation actors need independence. The NIST AI RMF Measure playbook recommends
   separate assessment teams and documentation of test sets, metrics, tools, methods, and
   outcomes. A role label alone is weaker than a captured, blinded grader record.
4. Holdout secrecy matters. TRUCE treats private evaluation data as a control against
   contamination. LiveBench likewise documents the validity loss caused by leaked test data
   and the bias risks of LLM judges. For local prompt optimization, the practical minimum is
   to freeze the dataset before the candidate, restrict holdout access to evaluation, and
   record that the optimizer did not see holdout results before selection.
5. Paired comparisons need paired execution evidence. The same task/trial and seed should be
   used for both variants. Their order should be counterbalanced so a systematic first-run or
   cache effect does not favor one variant. The validator must derive result fields from the
   captured trial artifact rather than trust duplicate receipt fields.

## engineer decision

- Upgrade the optimization receipt to schema version 2.
- Require an explicit fixed-benchmark or task-population estimand, measurement target,
  uncertainty method, and limitations; reject unsupported generalization claims.
- Bind it to one confined, digest-checked trial artifact.
- Require exact experiment bindings covering the changed variable, frozen environment,
  datasets, and gates.
- Require exact baseline/candidate trial coverage, identical paired seeds, counterbalanced
  order, non-empty outputs and traces, and blind independent graders.
- Derive pass, quality, safety, cost, latency, and infrastructure status from the artifact.
- Permit illustrative fixtures to validate contract structure, but never to authorize
  promotion. Only a `captured_run` may be promotion-eligible.
- Keep confidence intervals and richer hierarchical analysis as the next scale-up step when
  task and trial counts are large enough to support them; do not manufacture precision from
  the three-trial minimum.

## Limitations

Hash binding detects later mutation and receipt/artifact disagreement; it does not prove that
the recorder, runtime, or grader was honest. Stronger deployments should add signed CI
provenance, immutable raw logs, calibrated graders, and enough independent tasks and trials to
quantify uncertainty for the intended performance claim.

## Primary sources

- NIST, *Expanding the AI Evaluation Toolbox with Statistical Models*:
  https://www.nist.gov/news-events/news/2026/02/new-report-expanding-ai-evaluation-toolbox-statistical-models
- NIST, *Building Evaluation Probes into Agentic AI*:
  https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai
- NIST AI RMF Playbook, Measure:
  https://airc.nist.gov/airmf-resources/playbook/measure/
- Rajore et al., *TRUCE: Private Benchmarking to Prevent Contamination and Improve Comparative Evaluation of LLMs*:
  https://arxiv.org/abs/2403.00393
- White et al., *LiveBench: A Challenging, Contamination-Free LLM Benchmark*:
  https://arxiv.org/abs/2406.19314
