# Growth, conversion & funnel research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `growth-funnels.md`, `conversion-ui.md`

## Executive summary

2026 SaaS growth is **product-led by default** (~57% free trial, ~26% freemium).
Developer builds **instrumentation + conversion surfaces**; founder owns channels.

1. **Fix activation before acquisition** — median ~37.5%; below 25% = structural leak
2. **One activation event** — observable action predicting retention, not checklist completion
3. **TTV in first session** — target <15 min for PLG; every minute costs retention
4. **Sequential funnel optimization** — lowest stage conversion first
5. **Habit in week 1** — 3+ sessions → ~8× paid conversion vs one-time users
6. **PQL scoring** — product usage → sales; 2–4× MQL conversion
7. **No dark patterns** — trust compounds; tricks burn brands
8. **Instrument before optimizing** — stub analytics interface early

---

## 1. The AAARR funnel

**Sources**: Mixpanel PLG 2026, Kalungi bottleneck analysis, Arclen CRO playbook

```
Acquisition → Activation → Engagement → Revenue → Referral
```

| Stage | Key question | Owner split |
|---|---|---|
| Acquisition | Do the right people land? | Marketing + dev (SEO, perf) |
| Activation | Do they reach aha moment? | Product + dev (onboarding) |
| Engagement | Do they return? | Product (loops, email) |
| Revenue | Do they pay? | Product + pricing |
| Referral | Do they invite others? | Product (viral hooks) |

**Bottleneck method**: measure conversion between each stage for 30-day cohort.
Fix lowest relative conversion first — not always top of funnel.

---

## 2. Activation & benchmarks

**Sources**: ProductQuant 2026 benchmarks, Agile Growth Labs, Growth Unhinged

| Metric | Median / typical | Top performers |
|---|---|---|
| Activation rate (7d) | 37.5% | 50%+ |
| Onboarding checklist completion | 19.2% | — |
| PLG trial → paid | 15–25% B2B | 30%+ |
| Reverse trial → paid | 4–6% good | 8–12% |
| Form fields at signup | 3–5 max | email + password |

**Critical insight**: checklist completion ≠ activation. Users self-serve to value.
Don't block exploration with forced linear wizards.

**Industry variance**: AI/ML tools ~55% activation; FinTech ~5% — often product not marketing.

**TTV targets**:
- Simple: first session
- Medium: 1–3 days
- Complex enterprise: 7–14 days with human assist

---

## 3. PLG implementation architecture

**Sources**: ProductQuant PLG playbook 2026, Mixpanel

Developer builds:

### Milestone events

1. **Setup** — minimum config before value possible
2. **Activation** — first confirmed value (primary metric)
3. **Habit** — repeated value (D14/D30 return after activation)
4. **Upgrade intent** — pricing page, limit hit, feature gate click

### Data layer

- Event tracking (PostHog, Mixpanel, Amplitude)
- Funnel dashboards per cohort
- PQL score → CRM (HubSpot/Salesforce) via webhook or reverse ETL
- Feature flags for experiments

### Free tier design

- Free must deliver **real utility**
- Paid unlocks **scale** (seats, usage, advanced features)
- Reverse trial: premium features → downgrade (growing 7% adoption)

---

## 4. Landing & CRO (developer execution)

**Sources**: Arclen 2026 CRO, vezadigital patterns, HubSpot form studies, saasframe.io

### High-converting landing structure

1. Outcome headline (≤7 words)
2. Subhead — who it's for + key outcome
3. Primary CTA + optional social proof strip
4. Product visual (screenshot, terminal, demo)
5. 3-step "how it works"
6. Proof (logos, testimonials with attribution)
7. FAQ / objections
8. Final CTA

### Form CRO

- HubSpot: 11 → 4 fields = +120% conversion
- Formstack: >7 fields = 67.8% abandonment
- Progressive profiling post-signup (+42% lead-to-customer per Salesforce cited studies)

### Reading level

5th–7th grade — short sentences, outcome verbs, no jargon wall.

---

## 5. Retention & lifecycle

**Sources**: Mixpanel retention benchmarks, PLG re-engagement studies

### Retention curve

Plot weekly retention by signup cohort for 8 weeks.
- **Flattening** = habit formed
- **Decay to zero** = activation/product failure

B2B weekly retention global range ~45–78% (Mixpanel 2026) — gap often activation quality.

### Email triggers (behavior-based)

| Trigger | Timing | CTA |
|---|---|---|
| Signup, no activation | 24h, 72h | Finish setup → activation event |
| Activated, dormant | 7d | Return to specific feature |
| Trial ending | 7d, 3d, 1d | Upgrade with value recap |
| Usage 80% of limit | Immediate | Upgrade before hard block |

Cap marketing email; transactional unlimited.

---

## 6. Monetization psychology

**Sources**: Price Intelligently patterns, OpenView SaaS benchmarks

### Pricing page

- 3 tiers maximum
- Recommended tier highlighted (border/badge — semantic tokens)
- Annual toggle showing savings %
- Compare by **outcome** not feature laundry list

### Upgrade UX

- Contextual at feature gate — show what unlocks
- Usage meters before hard stop
- No modal on first session

### Trust on billing

- Clear cancel path in settings
- Export/data portability mentioned
- Security near payment form

---

## 7. Metrics hierarchy

**Sources**: Mixpanel PLG guide, ProductQuant, Kalungi

| Tier | Metrics |
|---|---|
| **North star** | Activation rate, NRR |
| **Leading** | TTV, D1/D7 retention, PQL count |
| **Lag** | MRR, churn, LTV:CAC |
| **Vanity (avoid)** | Raw traffic, signups without activation |

**NRR > 100%** = expansion exceeds churn — PLG sustainability signal.

Rule: improving activation 25% ≈ +34% revenue at same acquisition spend.

---

## 8. What developers build vs founders own

| Developers | Founders / growth |
|---|---|
| Landing pages, pricing UI, signup flows | Channel strategy, ad spend |
| Analytics event stubs + funnels | Interpretation + experiments |
| Empty states, onboarding UI | Activation event definition |
| Feature gates, usage meters | Pricing tiers, packaging |
| Email template components | Copy, sequences, timing |
| SEO metadata, performance | Content strategy |
| PQL score calculation | CRM thresholds, sales handoff |

Compose `unmachined` for copy; `cro` for experiment design.

---

## 9. Dark patterns to reject

- Fake countdown timers
- Hidden unsubscribe / cancel
- Pre-checked marketing opt-in
- Roach motel (easy in, hard out)
- Confirm-shaming ("No, I don't want to save money")
- Forced continuity after trial without clear notice

Legal risk (EU, FTC) + brand damage exceeds short-term lift.

---

## 10. Module map

| Topic | Reference |
|---|---|
| Funnel strategy, metrics, PLG | `growth-funnels.md` |
| Page layout, CTAs, hero | `conversion-ui.md` |
| Form UX | `design-patterns.md` |
| Performance (CWV) | `frontend-performance.md` |
| Copy quality | `unmachined` |
| Experiments | `cro` |

---

## Canonical sources

- https://mixpanel.com/blog/product-led-growth/
- https://productquant.dev/blog/saas-activation-benchmarks-by-industry-2026/
- https://productquant.dev/blog/plg-implementation-steps/
- https://arclen.io/blog/saas-cro-playbook-2026
- https://www.kalungi.com/blog/plg-funnel-bottleneck-analysis-saas-growth
- https://growthunhinged.com/ (PLG pricing surveys 2026)
