# Product analytics and KPI systems

**Last verified**: 2026-07-15 · **Review cadence**: 3 months
**Related**: `growth-funnels.md`, `product-onboarding.md`, `gtm-engineering.md`, `observability.md`

Product analytics measures whether software delivers user and business value. It is
separate from observability: analytics explains behavior/outcomes; telemetry explains
system health.

## KPI tree

```text
North Star (experienced value)
├── acquisition inputs
├── activation inputs
├── engagement/retention inputs
├── monetization/expansion inputs
└── guardrails: trust, quality, reliability, margin
```

Do not use signups, pageviews, raw messages, or spend as a North Star unless they
directly represent experienced value.

## Metric contract

Every metric must define:

```yaml
name: canonical name
question: decision it supports
formula: numerator / denominator / window
grain: user | account | workspace | event
source: authoritative tables/events
segments: required breakdowns
owner: accountable role
cadence: realtime | daily | weekly | monthly
freshness_slo: maximum acceptable lag
guardrails: metrics that must not regress
decision_rule: action at threshold
version: semantic definition version
```

No dashboard tile without a question, owner, and decision rule. For benchmark depth
(Rule of 40, NRR norms, CAC payback) and metric-selection theory, load the business-knowledge reference skill's
`business-analytics-decision-science` + `business-models-unit-economics`; this module
owns the contracts and instrumentation.

## Event contract

- past-tense `object_action` names (`project_created`, `checkout_completed`);
- immutable event id, occurred_at, received_at, actor/user, account, session, source;
- schema version and typed properties;
- server events for money, permissions, durable outcomes; client events for UI exposure/interactions;
- dedupe keys for retried server events;
- no secrets, raw prompts, payment data, or unnecessary PII.

## Core views

- funnel by cohort and segment;
- activation time-to-value distribution;
- retention curves and return-to-value behavior;
- conversion and revenue by acquisition cohort;
- plan/usage/margin by account segment;
- PQL→opportunity→won feedback;
- experiment effect plus guardrails;
- data-quality/freshness status.

## Experiment contract

Define hypothesis, exposure event, randomization unit, eligible cohort, primary metric,
guardrails, minimum detectable effect, duration/stop rule, and assignment persistence.
Do not peek-and-ship from noisy early results. Log exposure once and analyze intent-to-treat.

## Data quality gates

- event schemas validate at ingestion;
- identity merge and account membership are tested;
- client/server duplicates are reconciled;
- late events and timezone rules are explicit;
- metric SQL has fixtures for numerator, denominator, exclusions, and zero cases;
- dashboard freshness and source failures are visible.

---

Research: product analytics, experimentation, SaaS metrics, privacy-safe event design.

## Machine-checkable contract

Copy `templates/product-metrics/measurement-plan.sample.json`, adapt it, and run
`python3 scripts/validate-product-metrics.py <plan.json>`. The validator checks references,
critical-event idempotency, unsafe telemetry names, and privacy purpose/retention. It verifies
contract integrity; it cannot prove that a chosen metric represents customer value.
