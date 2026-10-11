# LLM ambiguity, incomplete implementation, and false-done research

**Verified**: 2026-07-16

Coding-agent failure is often evaluator-relative: the patch satisfies visible checks while missing the
intended behavior, constraints decay across long tasks, or the agent stops at a plausible intermediate
state. Stronger completion prose alone is insufficient. Engineer therefore binds accepted requirements
to outcome evidence, scans the affected implementation for unfinished substitutions, exercises real
boundaries, and treats unresolved blockers as incomplete.

Applied evidence:

- OpenAI's 2026 coding-evaluation audit identifies low-coverage tests as a path for incomplete fixes to
  pass and recommends deeper independent review of prompts, tests, patches, traces, and edge cases.
- Empirical SWE-bench studies find plausible patches that pass benchmark gates while failing broader
  developer tests, reinforcing that visible green tests do not establish semantic completion.
- Constraint-decay research reports declining joint satisfaction of functional and structural
  requirements as backend tasks grow more complex.
- Reward-hacking research shows agents can optimize observed reward while missing hidden objectives.
- FixedBench adds no-change tasks because agents must also recognize when implementation is already
  correct rather than mutate code reflexively.

Sources:

- OpenAI, [Separating signal from noise in coding evaluations](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)
- OpenAI, [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/)
- Software Lab, [SWE-bench patch correctness study](https://software-lab.org/publications/icse2026_SWE-bench-correctness.pdf)
- EURECOM, [Constraint decay in backend code generation](https://www.eurecom.fr/en/publication/8745)
- SRI Lab, [Coding Agents Don't Know When to Act](https://www.sri.inf.ethz.ch/publications/gloaguen2026coding)
- [Reward Hacking in Language Model Agents](https://arxiv.org/abs/2606.15385)
