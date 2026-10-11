# GTM engineering for product teams

**Last verified**: 2026-07-15 · **Review cadence**: 3 months
**Related**: `product-marketing.md`, `web-discovery-engineering.md`, `product-analytics.md`, `growth-funnels.md`, `compliance-privacy.md`

GTM engineering connects product behavior to acquisition, activation, sales, revenue,
retention, and expansion. It starts from a supplied ICP, offer, and motion. When the motion,
channel economics, or sales methodology itself is the question, load the business-knowledge reference skill's
`marketing-brand` / `sales-revenue` / `growth-retention-customer-success` for the knowledge
layer; this module owns the plumbing.

## Identity and funnel spine

```text
anonymous_id → user_id → account_id → billing_customer_id → crm_account_id
visit → qualified visit → signup/demo → activation → PQL → paid → retained → expanded
```

Identity merges must be deterministic, consent-aware, and reversible. Never join users
by fuzzy personal data.

## Attribution contract

Capture first-touch and last-touch separately:

- source, medium, campaign, content, term;
- referrer and landing route;
- experiment assignments;
- signup/demo conversion timestamp;
- account/user identity after consent and authentication.

Keep raw acquisition facts immutable; compute models downstream. "Direct/unknown" is
valid. Do not fabricate attribution.

## PQL and sales handoff

A product-qualified signal includes:

```yaml
signal: observed product behavior
account: stable account id
why_now: threshold crossed
evidence: event ids + timestamps
fit: explicit firmographic/plan criteria
owner: queue/team
next_action: bounded action
expires_at: signal freshness
```

PQL scoring must be explainable. Separate fit from intent. Suppress already-converted,
opted-out, unsupported, or recently-contacted accounts. Deduplicate handoffs.

## Closed-loop learning

- CRM stage changes and closed-won/lost outcomes return to analytics.
- Win/loss reason and objection taxonomy use controlled values plus notes.
- Channel reporting ties spend/effort to activated, retained, and revenue cohorts, not leads alone.
- Lifecycle messages stop when the user completes their target behavior.
- Expansion signals use value/usage evidence and respect contact preferences.

## Automation gates

Drafting, enrichment, scoring, and routing may automate. Sending outreach, changing CRM
ownership, creating paid campaigns, altering prices, or contacting customers requires
the relevant human/external-action approval.

## Verification

- replay the same source event: no duplicate lead, task, usage, or email;
- anonymous→known merge preserves both touches once;
- consent withdrawal suppresses non-essential processing;
- PQL reason is visible to the receiver;
- closed-loop outcome reaches the warehouse/dashboard;
- browser E2E covers lead/demo/signup handoff without sending real external messages.

---

Research: product-led sales, RevOps data contracts, attribution, lifecycle automation, privacy.
