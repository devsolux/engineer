# Growth & funnels: acquire, activate, retain, convert

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Product and marketing mechanics beyond page layout. For **page execution** see
`conversion-ui.md`. For **copy quality** compose `unmachined`. For **experiment
strategy** delegate `cro`.

Implementation contracts live in `product-analytics.md` (metrics/events),
`gtm-engineering.md` (identity/attribution/PQL/CRM), and
`product-business-engineering.md` (billing/revenue architecture). engineer stays a
product-engineering skill; general company strategy is outside this module.

Full research: `research/growth-research.md`

## Contents
- [The funnel model](#the-funnel-model)
- [Define your activation event](#define-your-activation-event)
- [Acquisition](#acquisition)
- [Activation & time-to-value](#activation--time-to-value)
- [Engagement & retention](#engagement--retention)
- [Monetization & conversion](#monetization--conversion)
- [Pricing models (2026)](#pricing-models-2026)
- [PQL and sales-assist](#pql-and-sales-assist)
- [Lifecycle messaging](#lifecycle-messaging)
- [Instrumentation (developer hooks)](#instrumentation-developer-hooks)
- [Metrics that matter](#metrics-that-matter)
- [Anti-patterns](#anti-patterns)

## The funnel model

```
Awareness → Acquisition → Activation → Engagement → Revenue → Referral
 ↑___________________________________________|
 (retention loop)
```

For PLG SaaS, optimize **sequentially** - fix the lowest conversion stage first:

| Stage transition | Healthy range (indicative) | Fix when |
|---|---|---|
| Signup → Activation | 35-50%+ | Below 25% = structural onboarding leak |
| Activation → Engagement | 60-70% | Retention curve doesn't flatten |
| Engagement → Paid | 20-30% | Value clear but no upgrade path |
| Free → Paid (trial) | No card 4-6% good, 10-15% great; card required 25-35% | Below "good" = pricing/value mismatch |

Anchors: activation (Userpilot 2025 avg 37.5%) and trial (ChartMogul/ProductLed
SaaS Conversion Report, Feb 2026). Engagement rows are unsourced heuristics.

**Highest ROI move**: activate users you already have before buying more traffic.
A 25% activation lift ≈ 34% MRR lift after 12 months in Appcues' illustrative model
(same signup volume, other metrics held fixed).

## Define your activation event

Before building onboarding, define **one observable action** that predicts retention:

```
Bad: "User completed onboarding checklist"
Good: "User created first project AND invited a teammate"
Good: "User ran first report with real data"
```

Process:
1. Cohort analysis - compare retained vs churned users at day 30
2. Find behavioral action with largest retention delta
3. Instrument as `activation_completed` event
4. Build onboarding to reach it in **first session** (target <15 min TTV)

Benchmark (Userpilot 2025, 62 B2B SaaS): average activation 37.5%; AI/ML tools 54.8%.
Checklist completion (avg 19.2%) ≠ activation - users find value off-path; don't force linear wizards.

## Acquisition

Developer implements **landing + SEO + speed**; founder owns channels.

| Channel | Dev responsibility |
|---|---|
| Organic / SEO | Metadata, sitemap, JSON-LD, Core Web Vitals, semantic HTML |
| Paid landing | Fast LCP, single CTA, conversion tracking hooks |
| Content / docs | Searchable docs route, code samples, llms.txt optional |
| Product virality | Invite flows, share links, embed widgets |
| App directories | Structured product pages, screenshots |

Landing rules (`conversion-ui.md`):
- One primary CTA above fold
- Outcome headline, not feature dump
- Product screenshot > abstract hero art
- 5th-7th grade reading level

## Activation & time-to-value

**Time-to-Value (TTV)** is the leading indicator of activation.

| Product complexity | Target TTV |
|---|---|
| Simple tool | First session (<15 min) |
| Medium SaaS | 1-3 days |
| Enterprise | 7-14 days (with human assist) |

Onboarding patterns:

| Pattern | When |
|---|---|
| **Empty state CTA** | Single action to first value ("Create project") |
| **Sample data** | Complex products - pre-filled demo workspace |
| **Progressive profiling** | Collect email first; defer profile fields |
| **Checklist (optional)** | Secondary - don't block exploration |
| **Reverse trial** | Full features 14 days → downgrade to free tier |

Remove every step that doesn't lead to activation event.

Forms: max 3-5 fields at signup. Imaginary Landscape (2008 before/after, 10→26 submits):
11→4 fields = +120% conversion rate.
Email + password or OAuth only at gate.

## Engagement & retention

Retention = habit formation. Users with **3+ sessions in week 1** convert to
paid far more often than one-time users (the quoted ~8× has no primary source; measure cohorts).

| Loop type | Example |
|---|---|
| **Usage loop** | More projects → more value → return |
| **Notification loop** | Email on meaningful event (not spam) |
| **Social loop** | Invite teammate → shared workspace |
| **Content loop** | Weekly report email pulls user back |

Build **retention curve** by cohort (8 weeks). Flattening baseline = product-market fit signal. Trend to zero = activation/habit failure - fix product, not ads.

Re-engagement triggers (behavior-based):
- Signed up, never activated → "Finish setup" (24h, 72h)
- Activated, dormant 7d → "Your projects miss you" + specific CTA
- Hit free limit → upgrade with context (which feature, which limit)

## Monetization & conversion

Upgrade moments (contextual, not modal spam):

| Trigger | Pattern |
|---|---|
| Feature gate | Inline upgrade prompt at point of need |
| Usage limit | 80% warning → 100% soft block + upgrade CTA |
| Team growth | "Invite more" hits seat limit |
| Trial ending | 7d, 3d, 1d emails + in-app banner |

Pricing page (`conversion-ui.md`):
- 3 tiers max; highlight recommended
- Annual toggle (show savings %)
- FAQ: cancel, export, security, refund

**Never** dark patterns: hidden cancel, roach motel, fake urgency timers.

## Pricing models (2026)

| Model | Share | Best for |
|---|---|---|
| Free trial | ~57% | B2B SaaS with clear TTV |
| Freemium | ~26% | Viral/network products |
| Reverse trial | ~7% | High feature depth; 4-12% conversion |
| Sales-led | Enterprise | ACV >$25k, complex procurement |

Shares: primary entry point, 200 products (ChartMogul/ProductLed/Poyar, Feb 2026).
Reverse trial: full access → auto-downgrade. Good conversion 4-6%; great 8-12% (small sample).

Freemium gate design:
- Free tier must deliver **real value** (not crippled demo)
- Paid tier unlocks **scale** (seats, usage, advanced features) not core utility

## PQL and sales-assist

**Product-Qualified Lead** - user hit usage threshold indicating buy intent.

```typescript
// lib/pql.ts - example scoring
export function scorePql(events: UserEvents): number {
 let score = 0;
 if (events.activationCompleted) score += 40;
 if (events.teamMembersInvited >= 2) score += 25;
 if (events.projectsCreated >= 5) score += 20;
 if (events.hitUsageLimit) score += 30;
 return score;
}
```

PQLs convert well above MQLs (Tunguz 2013: ~25-30% when sales calls them; quoted
PQL/MQL multipliers lack a primary source). Push scores to CRM (HubSpot/Salesforce)
via webhook or reverse ETL when sales-assist layer exists.

Developer hooks: emit events; marketing/sales owns thresholds.

## Lifecycle messaging

Email/product notification tiers:

| Tier | Examples | Frequency cap |
|---|---|---|
| Transactional | Reset password, receipt, invite | As needed |
| Lifecycle | Onboarding, trial ending | Max 1/day during sequence |
| Marketing | Newsletter, feature launch | Opt-in; unsubscribe required |

Every email: one CTA, plain language, mobile-readable.

In-app: toast for success; banner for account-level; modal sparingly.

## Instrumentation (developer hooks)

Stub analytics interface - vendor-agnostic:

```typescript
// lib/analytics.ts
type AnalyticsProps = Record<string, string | number | boolean>;

export function track(event: string, props?: AnalyticsProps) {
 if (typeof window === "undefined") return;
 // posthog.capture / plausible / gtag - project wires vendor
 window.__analytics?.track(event, props);
}

// Required events (minimum viable instrumentation)
export const Events = {
 SIGNUP_STARTED: "signup_started",
 SIGNUP_COMPLETED: "signup_completed",
 ACTIVATION_COMPLETED: "activation_completed",
 ONBOARDING_STEP_COMPLETED: "onboarding_step_completed",
 CTA_CLICKED: "cta_clicked",
 UPGRADE_VIEWED: "upgrade_viewed",
 UPGRADE_COMPLETED: "upgrade_completed",
 TRIAL_STARTED: "trial_started",
} as const;
```

Server-side: log conversion events to DB or warehouse for funnel queries.

Don't block ship on vendor - interface + event names first.

## Metrics that matter

| Metric | Definition | Why |
|---|---|---|
| Activation rate | % signups reaching activation event in 7d | Highest leverage |
| TTV | Time signup → activation | Leading indicator |
| D1/D7/D30 retention | % returning | Habit signal |
| Trial → Paid | % converting at trial end | Monetization health |
| NRR | Net revenue retention | PLG sustainability (>100% = expansion) |
| CAC payback | Months to recover acquisition cost | Unit economics |
| PQL → Opp | Product signal → sales pipeline | Hybrid PLG+sales |

Vanity metrics (de-prioritize): raw pageviews, total signups without activation.

## Anti-patterns

- Buying traffic before activation works
- Onboarding checklist ≠ activation event
- Forcing linear wizard when users self-serve to value
- Upgrade modal on first login
- Fake scarcity / countdown timers
- Hiding cancel / export
- Instrumenting nothing - flying blind
- Optimizing hero copy while activation is 12%
- Sales handoff without PQL scoring (too early or too late)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
