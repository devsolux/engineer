# Agentic engineering research - July 2026

This synthesis favors stable engineering rules over vendor-specific APIs.

## Findings adopted

- Agent quality is a property of the model and harness together. Evaluate end-state outcomes,
  trajectories, tool calls, cost, and latency; run repeated trials because one pass hides variance.
- Context is a finite control surface. Curated checkpoints and minimal relevant context outperform
  indefinite transcript growth for long-running work.
- Long-horizon work needs explicit initialization, incremental progress, persistent artifacts,
  rehydration, and environment-based verification.
- Workflow complexity should earn its place. Deterministic code and single-agent loops are the
  default; multi-agent graphs help when work is separable and coordination is explicit.
- Autonomy needs layered permissions, sandboxing, prompt-injection defenses, idempotent actions,
  failure thresholds, and human escalation for high-risk mutations.
- Capability evals and regression evals serve different jobs. Holdouts, reference solutions,
  balanced positive/negative tasks, calibrated graders, and trace reading reduce overfitting.
- Autonomous task reliability declines with task horizon and varies sharply by task. Plans must
  bound work and checkpoint progress instead of extrapolating short-task success.
- Indirect prompt injection should be evaluated as attacker-controlled sources reaching dangerous
  sinks. Instruction filtering alone is weak; permissions, sandboxing, network/data-flow policy,
  confirmations, telemetry, and end-to-end adversarial trials form the practical defense.

## Primary sources

- Anthropic, “Building effective agents” (2024-12-19): workflow and agent patterns; simplest
  sufficient architecture. https://www.anthropic.com/research/building-effective-agents
- Anthropic, “Effective context engineering for AI agents” (2025-09-29): minimal high-signal
  context, tool selection, compaction, and structured notes.
  https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic, “Effective harnesses for long-running agents” (2025-11-26): initializer/coding
  separation, incremental progress, persistent artifacts, and session handoff.
  https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic, “Demystifying evals for AI agents” (2026-01-09): outcome and transcript graders,
  repeated trials, capability versus regression suites, pass@k/pass^k, and grader validation.
  https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic, “Harness design for long-running application development” (2026-03-24): structured
  artifacts, decomposed work, and limits of prompt-only optimization.
  https://www.anthropic.com/engineering/harness-design-long-running-apps
- OpenAI, “A practical guide to building agents”: model/tool/instruction foundations,
  orchestration patterns, guardrails, failure thresholds, and human intervention.
  https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
- OpenAI, “The next evolution of the Agents SDK” (2026-04-15): controlled workspaces,
  snapshot/rehydration, sandbox execution, and injection-aware design.
  https://openai.com/index/the-next-evolution-of-the-agents-sdk/
- METR, “Task-Completion Time Horizons of Frontier AI Models” (updated 2026): empirical framing
  for success probability against human task duration. https://metr.org/time-horizons/
- OpenAI, “Designing AI agents to resist prompt injection” (2026-03-11): social-engineering and
  source-to-sink framing, sensitive transmission controls, sandboxing, and user consent.
  https://openai.com/index/designing-agents-to-resist-prompt-injection/
- NIST CAISI, “Insights into AI Agent Security from a Large-Scale Red-Teaming Competition”
  (2026-03-23): indirect injection attacks across tool, coding, and computer-use agents.
  https://www.nist.gov/blogs/caisi-research-blog/insights-ai-agent-security-large-scale-red-teaming-competition
- OWASP GenAI, “LLM06:2025 Excessive Agency”: minimize tools, permissions, and autonomous scope;
  require authorization downstream of model output.
  https://genai.owasp.org/llmrisk/llm062025-excessive-agency/
- Anthropic, “Quantifying infrastructure noise in agentic coding evals” (2026-02-05): resource
  configuration is an experimental variable and can materially distort coding-agent scores.
  https://www.anthropic.com/engineering/infrastructure-noise
- OWASP, “Top 10 for Agentic Applications” (2025-12-09): goal hijacking, tool misuse, identity
  and privilege abuse, agentic supply chain, unexpected code execution, memory poisoning,
  inter-agent trust, cascading failures, and rogue behavior.
  https://genai.owasp.org/2025/12/09/owasp-top-10-for-agentic-applications-the-benchmark-for-agentic-security-in-the-age-of-autonomous-ai/
- NIST NCCoE, “Identity and Authority of Software Agents” (2026-02-05): identification,
  authorization, auditing, non-repudiation, and prompt-injection controls for enterprise agents.
  https://www.nist.gov/news-events/news/2026/02/new-concept-paper-identity-and-authority-software-agents
- Anthropic, “SHADE-Arena” (2025-06-16) and “Sabotage evaluations” (2024-10-18): isolated
  environments for subtle harmful actions, code sabotage, sandbagging, and oversight attacks.
  https://www.anthropic.com/research/shade-arena-sabotage-monitoring

## Interpretation

The sources converge on a shift from prompt craft to harness engineering. engineer therefore treats
the PRD, goal, prompt, tools, state machine, checkpoint, graders, and evidence as one versioned
execution contract. This is an engineering inference, not a claim made verbatim by one source.
