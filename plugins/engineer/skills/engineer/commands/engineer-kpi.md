---
description: Design and implement a trustworthy product KPI tree, events, metrics, and dashboards.
---

# /engineer-kpi

Load `references/product-analytics.md`, `references/gtm-engineering.md`, and
`references/observability.md`.

1. Define North Star, inputs, outcomes, and guardrails.
2. Specify every metric's formula, grain, source, segments, owner, cadence, freshness, and decision rule.
3. Specify versioned client/server events and identity rules.
4. Plan warehouse/query/dashboard implementation and data-quality tests.
5. Keep product analytics separate from application observability while connecting incident annotations where useful.
6. For a non-trivial system, emit `templates/product-metrics/measurement-plan.sample.json`
   and run `python3 "$ENGINEER/scripts/validate-product-metrics.py" <plan.json>`.
