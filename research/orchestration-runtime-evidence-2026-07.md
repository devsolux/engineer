# Orchestration runtime evidence research - 2026-07

## Gap

A valid orchestration contract is still a claim about future behavior. The existing single-agent
trajectory receipt did not model concurrent workers, leases, delegation edges, parented spans,
isolated write lanes, joins, cancellation, or synthesis provenance. A manager could report success
while telemetry was incomplete or a worker exceeded authority.

## Primary-source findings

- OpenAI Agents SDK traces agent runs, generations, function tools, guardrails, and handoffs as
  parented spans in one workflow trace. Inputs, outputs, and tool payloads may contain sensitive data,
  so collection must be explicit and redacted by default.
- OpenAI run configuration exposes workflow, trace, group, tool-execution, and usage controls. A
  runtime receipt can retain stable identifiers and totals without copying sensitive prompt bodies.
- OpenTelemetry's GenAI conventions standardize workflow, agent, operation, tool, provider, usage,
  and conversation identifiers. Content-bearing attributes remain opt-in because they may contain
  PII or secrets.
- OWASP's agentic guidance calls for traceability and attribution because failures can propagate
  across agents and shared state. A final answer alone cannot reveal that cascade.

## engineer decision

Bind each run to the exact validated contract and each retained result to a local hash. Require one
worker record per contracted agent, lease release, bounded usage, exact handoff coverage, declared
tool sinks and write lanes, a coherent join, requirement-level artifact provenance, independent
verification, and a separate runtime reviewer. Treat dropped spans as an infrastructure error, not
an inferred success.

The validator checks captured evidence consistency. It cannot prove that instrumentation observed
events outside its collection boundary.

## Sources

- https://openai.github.io/openai-agents-python/tracing/
- https://openai.github.io/openai-agents-python/running_agents/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/
- https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
