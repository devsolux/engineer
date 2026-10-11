# engineer telemetry research

**Verified**: 2026-07-15

## Decision

Adopt opt-in, local, metadata-only telemetry derived from existing validated eval receipts. Do not add
always-on skill monitoring or a hosted observability dependency. This is proportional because engineer
already compares multiple hosts and versions; it needs reliable denominators and regression trends,
but prompt/code capture and developer-activity analytics add more privacy and governance risk than
decision value.

## Findings adopted

- OpenTelemetry GenAI conventions model agent, model, and tool spans plus token/duration metrics, but
  the conventions remain active work. Content capture is optional and sensitive.
- OpenTelemetry recommends low-cardinality span names, explicit use cases for attributes, and opt-in
  treatment for expensive, verbose, or sensitive values.
- Claude Code supports opt-in OTel metrics/events and beta traces. Prompt, tool-detail, tool-content,
  and raw API-body gates are disabled by default, but exported identity can include account and email
  attributes. Collector-side filtering is necessary for a privacy-preserving deployment.
- OpenAI Agents SDK traces generations, tools, handoffs, and guardrails. Sensitive generation/tool
  data can be disabled, and custom processors can replace the default exporter.
- Traces explain execution; graders establish quality. Cost, tokens, commits, or lines changed cannot
  substitute for task outcomes, safety, or human-calibrated evaluation.

## Rejected now

- Automatic telemetry on every invocation.
- Prompt, response, code, file path, URL, shell command, or tool-result capture.
- A new SaaS telemetry dependency or mandatory collector.
- Developer leaderboards, productivity scores, or rankings from activity metrics.
- Treating provider-native spans as host-neutral behavioral proof.
- High-cardinality session, account, repository, branch, or file labels.

## Revisit hosted OTel when

- local ledgers from repeated trials are difficult to compare or retain safely;
- more than one operator needs shared dashboards and access control;
- incident response needs central audit correlation;
- a reviewed collector can redact identities/content before durable storage; and
- retention, deletion, RBAC, cost, sampling, and convention-version ownership are assigned.

## Primary sources

- OpenTelemetry, [Inside the LLM Call: GenAI Observability with OpenTelemetry](https://opentelemetry.io/blog/2026/genai-observability/), 2026-05-14.
- OpenTelemetry, [How to write semantic conventions](https://opentelemetry.io/docs/specs/semconv/how-to-write-conventions/), current 2026-07-15.
- OpenTelemetry, [Semantic conventions](https://opentelemetry.io/docs/specs/semconv/), v1.43.0 observed 2026-07-15.
- Anthropic, [Claude Code monitoring](https://code.claude.com/docs/en/monitoring-usage), current 2026-07-15.
- Anthropic, [Agent SDK observability](https://code.claude.com/docs/en/agent-sdk/observability), current 2026-07-15.
- OpenAI, [Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/), current 2026-07-15.
- OpenAI, [Agents SDK configuration](https://openai.github.io/openai-agents-python/config/), current 2026-07-15.
