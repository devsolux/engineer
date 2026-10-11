# Multi-agent orchestration research - 2026-07

## Gap

engineer already explained when manager, specialist, parallel-worker, or durable-workflow patterns are
useful. It did not make a launch plan falsifiable. A prompt-only plan could still create authority,
share mutable lanes, oversubscribe budget, leak full history, wait forever at a join, orphan workers,
or synthesize unsupported consensus.

## Current primary-source findings

- OpenAI Agents SDK separates manager agents-as-tools from control-transferring handoffs. Handoffs
  support typed metadata and input filters; receiving the full history is not always appropriate.
- OpenAI notes that input guardrails apply to the first agent and output guardrails to the final
  agent. Intermediate tool calls therefore need tool-level controls.
- Its tracing model parents agent, generation, function-tool, guardrail, and handoff spans under one
  workflow trace. Model and tool payloads may contain sensitive data and need an explicit capture
  policy.
- OpenTelemetry defines generative-AI agent and operation spans so agent workflows can join the
  rest of a system trace without inventing unrelated telemetry semantics.
- OWASP's agentic guidance treats inter-agent trust and cascading propagation as distinct risks.
  More workers increase blast radius unless authority, state, fan-out, and cancellation are bounded.

## engineer decision

Add a pre-launch contract and validator. It models an acyclic task graph by default, requires child
authority to be a subset of both sender and receiver capabilities, assigns non-overlapping write
lanes, reserves budget for synthesis, defines join and failure behavior, defaults traces to redacted,
and prevents illustrative fixtures from approving execution.

The first contract validates declared intent. Runtime traces and end-state evidence remain necessary
to prove compliance.

## Sources

- https://openai.github.io/openai-agents-python/multi_agent/
- https://openai.github.io/openai-agents-python/handoffs/
- https://openai.github.io/openai-agents-python/tracing/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
