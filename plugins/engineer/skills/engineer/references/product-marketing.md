# Product marketing implementation

**Last verified**: 2026-07-15 · **Review cadence**: 3 months
**Related**: `conversion-ui.md`, `seo-metadata.md`, `web-discovery-engineering.md`, `growth-funnels.md`, `product-analytics.md`

This module turns an accepted positioning/offer into product surfaces and evidence.
It does not perform general brand strategy or company management.

## Required brief

Before building, capture:

```yaml
icp: specific buyer/user
job: painful job or desired outcome
trigger: why they act now
alternative: what they do today
promise: measurable outcome
proof: demos, benchmarks, customers, or receipts
objections: top 3-5
primary_cta: one next step
activation_event: first experienced value
```

Unknown fields are explicit assumptions, not invented facts.

## Surface map

| Buyer question | Product surface |
|---|---|
| Is this for me? | hero + ICP/use-case language |
| Will it work? | real demo, proof, architecture/security facts |
| How is it different? | alternative-aware comparison |
| What does it cost? | transparent pricing/value metric |
| Is it safe? | security, privacy, reliability, support |
| What happens next? | CTA + expectation + low-friction start |

For technical products, product truth beats adjectives: working example, latency,
compatibility, limits, docs, and failure behavior.

## Launch implementation checklist

- Positioning vocabulary is consistent across metadata, page, onboarding, email, and app.
- One canonical product fact source feeds page/schema/docs to prevent claim drift.
- Proof has provenance and dates; placeholder logos/metrics are visibly marked or removed.
- CTA event, signup source, activation, PQL, purchase, retention, and referral are connected.
- Comparison pages are factual, dated, and respectful; no unverifiable superiority claims.
- SEO/AEO content renders server-side with accurate JSON-LD.
- Social cards, screenshots, demo flows, changelog, docs, and support readiness are checked.

## Sales-enablement surfaces

- shareable use-case pages by ICP/job;
- ROI/value calculator with visible assumptions;
- security/architecture page and downloadable factual answers;
- plan/limit comparison and procurement FAQ;
- demo workspace seeded with credible synthetic data;
- objection-linked proof, not generic feature lists.

Keep sales material tied to the canonical fact source: feature availability, limits, security,
compliance, support, pricing, implementation status, and proof expiry. Generate role- and stage-specific
views from the same facts rather than cloning decks that drift. Track an asset's contribution through
qualified progression and activation; downloads and opens are diagnostic, not business outcomes.

## Quality gate

Test comprehension with five questions: who it is for, what outcome, why different,
what proof, what next. If a tester cannot answer from the first screen and relevant
detail page, hierarchy or copy is not done.

---

Research: product marketing, technical buyer journeys, conversion UX, SEO/AEO; re-verify channel-specific claims before use.
