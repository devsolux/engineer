# Agent trajectory evaluation research

**Date**: 2026-07-16

## Decision

Multi-turn agents need both outcome and trajectory evidence. A claimed final answer is weaker than
the environment state, while an end-state test alone can miss unsafe, wasteful, or policy-breaking
paths. Engineer therefore keeps deterministic state-machine checks close to the execution contract and
reserves model or human grading for semantics that code cannot establish.

The local trajectory validator now enforces:

- contiguous ordered events within the contract step budget;
- known tools, approvals, sinks, transfer confirmation, and paired action observations;
- explicit observation outcome, evidence, and state identity;
- planned steps before completion claims;
- checkpoints matching the latest observed state;
- a checkpoint after the final action and observation before success;
- all plan and acceptance IDs, passing verification, and exactly one final stop;
- declared non-success stop reasons and bounded no-progress state repetition;
- direct regular trajectory and contract inputs rather than symlink aliases.

This is path-structure evidence, not provider truth. It cannot prove omitted events, tool honesty,
environment state, semantic evidence sufficiency, or that a hash names the claimed state. Completion
still replays contract-defined outcome artifacts and independent review. Behavioral promotion still
uses repeated trials because agent behavior is nondeterministic.

## Primary sources

- Anthropic, *Demystifying evals for AI agents*: multi-turn transcripts, environment outcomes,
  combined deterministic/model/human graders, repeated trials, transcript review, and capability
  versus regression suites: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic tool-use loop: client tools require explicit request, execution, result, and stop-reason
  handling: https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works
- OpenAI agent tooling: tracing and evaluations for observing workflow execution:
  https://openai.com/index/new-tools-for-building-agents/
