# Product-business engineering

**Last verified**: 2026-07-17 · **Review cadence**: 3 months
**Related**: `product-analytics.md`, `gtm-engineering.md`, `billing-*`, `growth-funnels.md`, `composition.md`

engineer is a product-engineering skill. This module makes stated business goals
executable in the product; it is not a CEO OS, fundraising advisor, portfolio
manager, or general business-strategy router.

When the task needs the business knowledge itself - which pricing model fits, what CAC
payback is healthy, how a term sheet or rev-share clause works - load the matching
**business-knowledge reference skill** domain module (`pricing-monetization`, `business-models-unit-economics`,
`sales-revenue`, `fundraising-capital-markets`, `negotiation-dealmaking`...) for frameworks,
benchmarks, and formulas, then translate here. The business decision stays with the user or
the private strategy skill; engineer builds the accepted choice (boundary: `composition.md`).

## Translation contract

Turn each accepted goal into:

| Business input | Engineering output |
|---|---|
| ICP + job | roles, journeys, permissions, seeded demo |
| Offer + packaging | entitlements, limits, billing/metering |
| GTM motion | signup/demo/contact paths, identity + attribution |
| Activation definition | event contract, onboarding state, dashboard |
| PQL definition | computed signal, explainability, CRM handoff |
| Retention goal | cohort events, health signals, lifecycle triggers |
| Expansion model | usage/seat thresholds, upgrade prompts, sales signal |
| KPI target | formula, source, owner, cadence, guardrail, alert |
| Product strategy | outcome tree, opportunity/evidence links, bets, release/kill gates |
| Sales motion | lead/account lifecycle, qualification evidence, consent, CRM handoff, SLA |
| Business development | partner application, attribution, entitlement, contract and rev-share states |
| Company operating policy | role permissions, approval workflow, audit log, reporting and escalation |

## Business-ready feature brief

```yaml
goal: business outcome
user_outcome: value delivered
segment: intended users/accounts
mechanism: why product behavior should move the outcome
primary_metric: formula + source
guardrails: retention, margin, quality, trust
events: names + properties + identity
surfaces: routes/components/jobs/integrations
experiment: exposure unit + cohort + decision rule
owner: accountable role
risks: privacy, bias, billing, support, abuse
```

No build begins from "increase revenue" alone. State the user mechanism and leading
product behavior.

## Product-management engineering

- Requirements link user evidence and business outcome to stable acceptance IDs, telemetry, release
  controls, support readiness, and a named decision owner.
- Roadmap labels are hypotheses and sequencing commitments, not proof of value. Record dependencies,
  confidence, cost of delay, reversible scope, and the signal that continues, changes, or kills a bet.
- Ship to a deliberate cohort, assess functional, UX, technical, trust, and customer impact, then
  iterate or stop. Output volume and feature adoption alone do not establish value.
- Feedback retains source, segment, recency, frequency, severity, and evidence. Do not turn the
  loudest request or largest account directly into a universal feature.

## Sales and business-development engineering

- Define lifecycle states and allowed transitions for lead, PQL, opportunity, trial, contract,
  partner, renewal, expansion, loss, and reactivation. Preserve source and reason history.
- Qualification is explainable and correctable. Never infer sensitive traits or let an opaque score
  silently deny service, support, pricing, or human review.
- Handoffs are idempotent, consent-aware, deduplicated, owned, timed, observable, and reversible.
  CRM, billing, support, product identity, and warehouse records need an explicit reconciliation rule.
- Quotes, discounts, approvals, territories, commissions, referrals, partner attribution, and
  revenue share use durable server-side policy with effective dates and audit trails.
- Sales enablement surfaces use current product facts, scoped proof, security answers, plan limits,
  procurement status, and honest implementation timelines. Do not synthesize customer evidence.

## Company-operations engineering boundary

Engineer can implement an accepted operating policy: permissions, approval chains, KPI definitions,
meeting inputs, decision logs, audit trails, alerts, integrations, and management dashboards. Load
`company-operating-system.md` when implementation crosses executive functions, governance, people,
finance, or legal operations. The private strategy skill owns company strategy, organization design, leadership judgment,
hiring, capital allocation, and founder decisions. If the task asks what the company should do,
route to the private strategy skill; if it asks how the chosen policy becomes reliable software and evidence, Engineer owns
execution.

## Revenue architecture

- Entitlements are server-enforced and sourced from durable billing state.
- Usage is idempotently metered with unit, timestamp, account, source event, and dedupe key.
- Margin-sensitive AI work records model/provider/unit cost without exposing prompts or secrets.
- Pricing experiments apply to explicit cohorts; assignment is stable and auditable.
- Discounts, trials, credits, refunds, and grandfathering are first-class states.
- Never grant paid access from a client redirect.

## Scope boundary

Outside engineer core: venture scoring, fundraising, founder psychology, hiring plans,
portfolio allocation, and channel content operations. engineer can implement software
for an already selected policy, but it does not pretend to own those decisions.
For those domains, a business-knowledge reference skill carries the reference knowledge, the
private strategy skill owns the live decision, and a venture-artifact skill produces the artifact packs.

---

Research: SaaS/product engineering, billing, analytics, RevOps integration, trustworthy experimentation.
