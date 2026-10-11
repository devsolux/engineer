# Proving attribution in prompt and agent-loop experiments

**Date:** 2026-07-15

## Gap

Repeated paired trials can show a difference between two systems, but they cannot attribute that
difference to a prompt instruction when the tool manifest, context policy, loop budget, model,
grader, or runtime also changed. A `changed_variables` label is not proof of experimental control.

## Findings

- OpenAI's API guidance recommends pinned model snapshots because prompt behavior can change
  between model versions. Evals metadata also supports prompt-version tracking. Version names are
  useful indexes, but the tested content and configuration still need immutable identities.
- OpenAI's prompt-management guidance keeps version history and reruns linked evals after prompt
  publication. That supports explicit variant identity rather than an unrecorded text edit.
- Recent environment-grounded prompt-optimization research separates agent components and uses
  behavior analysis to target revisions before environment rollouts. The causal lesson is to
  identify the responsible component and keep unrelated components fixed.
- Recent judge-optimization research reports judge-specific overfitting: changing or exposing the
  optimizer to a different grader can produce apparent gains that do not transfer. Grader identity
  therefore belongs inside the controlled variant bundle.
- A digest of each complete variant is not enough by itself. It proves identity but does not show
  what differed. A deterministic structural diff provides both integrity and attributable scope.

## engineer decision

1. Store baseline and candidate configurations in one confined, hash-bound JSON bundle.
2. Give each variant exactly eight sections: version, prompt, context, tool, loop, model, grader,
   and environment. This makes hidden co-interventions visible.
3. Declare one allowed JSON pointer beneath the named changed layer.
4. Recursively compare strict JSON types, object keys, array positions, and scalar values. The
   observed leaf-diff set must equal the declared pointer set exactly.
5. Bind human baseline/candidate version names to the bundle versions.
6. Cross-check frozen model, temperature, tool manifest, harness, repository fixture, and resource
   class against both variants unless that exact layer is the controlled intervention.
7. Include the variant bundle path and digest inside the experiment binding already signed by the
   captured trial artifact.

## Limits

Structural equality proves that recorded JSON configurations differ in one place. It does not
prove that an opaque model endpoint, tool server, retrieved corpus, or harness honored the recorded
configuration. Use immutable model IDs, content digests, captured requests, and trusted runtime
provenance where those boundaries matter. A one-path change can still have broad behavioral effects;
the safety, holdout, cost, latency, and trace gates remain necessary.

## Primary sources

- OpenAI API reference, model snapshot and eval guidance:
  https://platform.openai.com/docs/api-reference/introduction
- OpenAI, prompt management and version history:
  https://help.openai.com/en/articles/9824968
- Fernandes et al., *Environment-Grounded Automated Prompt Optimization for LLM Game Agents*:
  https://arxiv.org/abs/2606.17838
- Elganayni et al., *Exploiting LLM-as-a-Judge Disposition on Free Text Legal QA via Prompt Optimization*:
  https://arxiv.org/abs/2604.20726
