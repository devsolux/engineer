# Conversion UI - router

**Last verified**: 2026-08-21 · **Review cadence**: 3 months

Router for **page-level conversion execution**. Strategy and lifecycle live in
sibling modules.

| Topic | Module |
|---|---|
| Funnel stages, activation, retention, PLG | `growth-funnels.md` |
| Page layout, CTAs, hero, pricing UI | This file (sections below) |
| Forms UX | `design-patterns.md` |
| Tokens, hierarchy | `design-system.md`, `design-patterns.md` |
| Aesthetic / structure choice | `design-taste.md` |
| Copy anti-slop | `unmachined` |
| Experiment design | `cro` |

Full research: `research/growth-research.md`

Behavioral mechanisms must pass `behavioral-design.md`: truthful proof and urgency,
visible decline/cancel paths, reversible consequential actions, accessible choices,
and user-value guardrails alongside conversion.

## Contents
- [Page job statement](#page-job-statement)
- [Landing page anatomy](#landing-page-anatomy)
- [Hierarchy and friction](#hierarchy-and-friction)
- [Trust and proof](#trust-and-proof)
- [CTA discipline](#cta-discipline)
- [Forms that convert](#forms-that-convert)
- [SaaS surface patterns](#saas-surface-patterns)
- [Measurement hooks](#measurement-hooks)
- [Config-driven pages](#config-driven-pages)
- [Anti-patterns](#anti-patterns)

## Page job statement

Before writing code, one sentence:

> A **[persona]** on this page needs to **[primary action]** because **[motivation]**.

Every page: **one primary action**. Secondary actions look secondary.
Load `design-taste.md` before layout. The list below is a content checklist, not
a required DOM order. Do not emit Hero → 3 icon cards → logos → CTA as the default.

## Landing page anatomy

1. **Hero** - the most characteristic thing in the product's world, plus primary CTA
2. **Problem → outcome** - only if the page must teach; skip if the product is visible
3. **How it works** - 3 steps with verbs when order matters; otherwise omit numbering
4. **Proof** - real logos, metrics, testimonials — never invented
5. **Objection handling** - FAQ / comparison when the sale needs it
6. **Final CTA** - repeat primary action

Rules:
- Headline ≤7 words when possible; max 2 lines
- Primary CTA visible at 375px without scroll
- Product screenshot/terminal > abstract 3D
- Preserve message match from ad, search result, email, referral, or sales handoff through headline,
  offer, proof, and CTA. Split materially different intent into dedicated pages.
- Put material price, renewal, eligibility, limitation, and delivery facts before commitment. A page
  may persuade; it may not manufacture scarcity, disguise sponsorship, or hide mandatory cost.
- Render the primary meaning and CTA without client JavaScript. Reserve hero dimensions, bound
  third-party tags, and measure field Core Web Vitals by page type and acquisition segment.

## Portfolio and case-study pages

- Lead with the work category, audience, constraint, role, and verifiable outcome—not a cinematic intro.
- A case study shows problem, baseline, decisions, contribution boundaries, implementation evidence,
  result, limitations, and what changed afterward. Separate team results from personal contribution.
- Provide a fast project index with filters that remain usable as ordinary links. Each item has a
  stable URL, meaningful preview, alt text, readable artifact, and contact or next-step route.
- Protect client secrets and unreleased work. Mark reconstructed, synthetic, redacted, and concept
  artifacts. Never invent a client quote, metric, logo permission, or role.
- Motion and WebGL are progressive enhancement. The portfolio must retain navigation, content,
  keyboard operation, reduced-motion behavior, mobile performance, and crawlable project detail.

## Hierarchy and friction

| Element | Treatment |
|---|---|
| Primary CTA | Default `Button`, one per viewport section |
| Secondary | `outline` / `ghost` |
| Tertiary | text link |
| Nav | Minimal on landing; strip on pure conversion pages |

Friction reduction:
- Signup: email + password or OAuth - defer profile to post-auth
- Checkout: progress indicator, saved payment
- Onboarding: one decision per screen

## Trust and proof

- Real metrics or `[placeholder]` labels - never invented numbers
- **Proof sits beside the claim it supports**, not pooled at the bottom
- **Risk reversal near the primary CTA**: at least one of free trial / free
  plan / no credit card / cancel anytime / guarantee — only terms that are
  actually true (`behavioral-design.md`)
- High-friction offers: move objection handling (FAQ/comparison) earlier
- Testimonials: name, role, company, avatar
- Security badges near auth/payment
- Privacy/terms on signup

## CTA discipline

Verb + outcome:
- ✅ "Start free trial" / "Create your first project"
- ❌ "Submit" / "Learn more" (as primary)

Placement: hero, post-proof, optional sticky mobile bar, final section.

## Forms that convert

See `design-patterns.md` for full form UX. Conversion-specific:
- Max 3-5 fields at signup gate
- Social proof adjacent to form
- Success state confirms next step

## SaaS surface patterns

| Surface | Primary goal | Key pattern |
|---|---|---|
| Landing | Signup | Outcome hero → proof → CTA |
| Pricing | Plan select | 3 tiers, recommended badge |
| Signup | Account created | Minimal fields → activation path |
| Empty dashboard | First value | Single CTA + one-line instruction |
| Upgrade gate | Revenue | Contextual inline, not spam modal |
| Billing settings | Retention | Clear plan, usage, honest cancel |

## Measurement hooks

See `growth-funnels.md` § instrumentation. Every primary CTA:

```typescript
track(Events.CTA_CLICKED, { location: "hero", label: "start_free_trial" });
```

Pair CTA clicks with page-view eligibility, successful form or purchase completion, activation, lead
quality, refund/cancel, retention, performance, and trust guardrails. Optimize for qualified outcomes,
not click-through alone. Segment by intent, source, device, new/returning status, and experiment arm;
avoid reading causality from an unrandomized dashboard.

## Config-driven pages

```typescript
// lib/site.ts
export const site = {
 name: "Product",
 tagline: "Outcome in one line.",
 links: { app: "/signup", docs: "/docs", pricing: "/pricing" },
 lastUpdated: "2026-07-12",
} as const;
```

## Page completeness

Unfinished tells that survive review — check before ship:

- Dead links or `#` hrefs: link it or visually disable it; current nav item indicated
- Branded 404; favicon; privacy/terms in the footer
- Skip-to-content link; alt text on meaningful images
- Client-side validation on form fields (email format, required)
- `<title>`, meta description, `og:image` (depth: `seo-metadata.md`)

## Anti-patterns

- Feature-first headlines without outcome
- Multiple primary buttons per viewport
- Signup wall before any value signal
- Carousel hero (LCP + hidden CTA)
- Fake urgency, entry modal, hidden cancel
- 5+ pricing tiers

Build flow: `growth-funnels` (strategy) → `conversion-ui` (layout) → `engineer design` → `unmachined` (copy).

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
