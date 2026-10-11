# Anti-slop and deliberation research - July 2026

## unmachined findings adopted

The local repository at `https://github.com/devsolux/unmachined` was inspected at commit
`26f3fdfb50c659ed6ef4c0d110a41bf11bb340ef` (2026-07-14). engineer adopts these parts:

- Write under the rules from the start; do not generate filler and clean it afterward.
- Deterministic severity-tiered text and UI checks before model self-review.
- Truth preservation for facts, numbers, identifiers, quotations, units, URLs, and scope.
- Variety across outputs so a fixed anti-default style does not become a second monoculture.
- Separate text and rendered-interface checks, with accessibility and browser evidence retained.
- Always-on configuration for human-facing output and explicit disclosure when scanning is absent.

engineer does not use unmachined as an authorship detector. Research on stylometric classification
shows measurable signals, but performance depends on genre, passage length, model, language, and
editing. Short samples can produce false positives. The safe use is linting artifacts you control,
not accusing authors or making disciplinary decisions.

Primary and project sources:

- devsolux, unmachined: deterministic tell catalogs, always-on policy, scanner, detection caveats,
  and second-order monoculture. https://github.com/devsolux/unmachined
- Tufts/CMU et al., "Model-Specific Language Model Idiosyncrasies" (ICML 2025): model-specific
  lexical distributions survive transformations. https://arxiv.org/abs/2502.12150
- "Stylometric detection of AI-generated texts" (Digital Scholarship in the Humanities, 2026):
  interpretable signals and false-positive sensitivity on shorter samples.
  https://academic.oup.com/dsh/advance-article/doi/10.1093/llc/fqag064/8714041
- "Stylometric comparisons of human versus AI-generated creative writing" (2025): quantitative
  differences require qualitative interpretation and careful assumptions about human baselines.
  https://www.nature.com/articles/s41599-025-05986-3

## Council findings adopted

The local repository at `https://github.com/devsolux/council-of-high-intelligence` was inspected at
commit `83e2dd39a1b0cdd6c4455b62af23ed37bed2948b` (2026-07-14). engineer adopts the protocol where it
improves engineering judgment:

- A problem-restatement gate before analysis.
- Independent blind-first positions followed by anonymized cross-review.
- Diversity of reasoning methods and, when available, model families.
- Anti-conformity prompts, dissent quotas, counterfactuals, and bounded rounds.
- An independent synthesizer, explicit vote accounting, minority report, unresolved questions,
  acceptable compromises, kill criteria, and a single owned next action.
- Honest no-consensus outcomes when the evidence does not support a winner.

engineer does not copy the 18 personas, provider router, or full protocol into routine work. Research
on multi-agent debate is conditional: diversity can help, but debate can also amplify conformity,
self-confidence, correlated errors, and cost. Deliberation must beat a strong single-agent or
deterministic baseline on a task-relevant eval before becoming the default.

Primary and project sources:

- devsolux, Council of High Intelligence: multi-round protocol, method diversity, anonymization,
  anti-conformity, independent chair, and decision receipts.
  https://github.com/devsolux/council-of-high-intelligence
- "Can LLM Agents Really Debate?" (2025): controlled study of when debate succeeds or fails.
  https://arxiv.org/abs/2511.07784
- "Revisiting Multi-Agent Debate as Test-Time Scaling" (2025): debate effectiveness is conditional
  and must be compared at controlled compute budgets. https://arxiv.org/abs/2505.22960
- "Advancing Collaborative Debates with Role Differentiation" (ACL 2025): differentiated roles can
  improve collaborative debate. https://aclanthology.org/2025.acl-long.1105/
- "Multi-LLM-Agents Debate" (ICLR 2025): conformity varies across models and interaction settings.
  https://proceedings.iclr.cc/paper_files/paper/2025/file/1da9ca7e9cef4b1af63913f05d1630a4-Paper-Conference.pdf

## engineer design decision

unmachined is a default human-facing output gate because it is cheap, deterministic, and catches
known defects without adding model calls. Council remains optional because its benefit depends on
decision ambiguity and method/model diversity, while its cost grows with seats and rounds. Both
compose through explicit boundaries so engineer remains its own standalone engineering skill.
