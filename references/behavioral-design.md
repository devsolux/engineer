# Behavioral design for trustworthy product outcomes

**Last verified**: 2026-07-15 · **Review cadence**: 6 months
**Related**: `design-patterns.md`, `design-accessibility.md`, `conversion-ui.md`, `product-onboarding.md`

Behavioral design helps users understand value and complete intended work. It
must not coerce, deceive, obstruct exit, or manufacture evidence.

## Ethical gate

Every behavioral mechanism must pass all six:

1. **Truthful:** claims, scarcity, defaults, testimonials, and prices are real.
2. **Autonomous:** declining is visible and does not punish unrelated use.
3. **Reversible:** consequential choices have undo, confirmation, or recovery.
4. **Proportionate:** urgency and friction match actual risk.
5. **Accessible:** no reliance on color, motion, shame, or cognitive overload.
6. **Measurable benefit:** success includes user value, not conversion alone.

Reject fake countdowns, confirmshaming, hidden unsubscribe/cancel paths, disguised
ads, preselected paid options, forced continuity, fabricated social proof, and
obstruction-by-friction.

## Practical mechanisms

| Goal | Use | Guardrail |
|---|---|---|
| Reduce uncertainty | previews, examples, transparent progress | show limitations and cost |
| Help first success | one activation CTA, progressive disclosure | allow skip and return |
| Reduce effort | smart defaults, saved state, autofill | defaults must be safe and editable |
| Build confidence | receipts, status, undo, audit history | no invented proof |
| Encourage return | meaningful progress, reminders | preference controls + suppression |
| Clarify choice | comparison table, recommended fit | disclose recommendation basis |

## Decision architecture

- One primary action per decision surface.
- Put consequences next to the action, not behind a tooltip.
- Use recognition over recall: show prior choices and current state.
- Break complex work into meaningful chunks; never split merely to inflate completion.
- For destructive actions: explicit object name, consequence, recovery window if possible.
- For pricing: show billing unit, renewal cadence, limits, overage behavior, and cancellation terms.

## Measurement

Pair conversion with guardrails:

| Outcome | Guardrails |
|---|---|
| Signup completion | activation, early churn, support contacts |
| Upgrade | refund/cancel rate, margin, retention, complaint rate |
| Onboarding completion | time-to-value, task success, skip rate |
| Notification click | opt-out, complaint, downstream value event |

Segment by role, device, acquisition source, and new/returning user. Do not optimize
an aggregate that hides harm to a smaller group.

## Browser QA prompts

- Can a user say no as easily as yes?
- Does back/refresh preserve safe state?
- Are total price and future consequences visible before submit?
- Does keyboard/screen-reader order match the visual decision order?
- Can a user recover from a mistaken action?
- Is urgency backed by a real expiring condition?

---

Research: behavioral economics, humane design, WCAG, consumer-protection dark-pattern guidance.

Primary references: [FTC dark-pattern staff report](https://www.ftc.gov/reports/bringing-dark-patterns-light)
and [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/).
