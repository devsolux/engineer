# Metered / usage-based billing (Stripe)

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Usage records, meters, and overage on the default stack.
Load with `billing-stripe.md`, `billing-seats.md` (seat quantity is not usage),
`backend-webhooks.md`, `background-jobs.md`, `audit-log.md`. Whether usage pricing
fits at all is business-knowledge reference-skill `pricing-monetization` knowledge; this module implements it.

## When to use

| Model | Module |
|---|---|
| Flat subscription per seat | `billing-seats.md` |
| Included quota + overage (API calls, tokens, storage GB) | **this module** |
| Pure prepaid credits | Product-specific; still report usage for UX |

Do not invent custom card charging. Use Stripe meters / usage records + invoices.

## Concepts

| Term | Meaning |
|---|---|
| Meter / metered price | Stripe price that bills from reported usage |
| Usage record | Timestamped quantity for a subscription item |
| Aggregation | sum / max / last_during_period (match product) |
| Soft limit | UX warn before hard block |
| Hard limit | Reject work until upgrade or period reset |

## Architecture

```text
Product event (API call, embed job, export)
 -> auth + entitlement check (plan + remaining quota)
 -> do work
 -> durable job: reportUsage(orgId, meter, quantity, idempotencyKey)
 -> Stripe usage / meter API
 -> optional: update local usage counter for UX
Webhook: invoice.paid / payment_failed (same as subscription)
```

| Rule | Why |
|---|---|
| Report usage **after** successful work (or define policy) | Don't bill failed jobs unless product says so |
| **Idempotency key** per logical event | Retries must not double-bill |
| Durable job for Stripe report | Request path timeouts |
| Local counters for UI only | Stripe remains source of truth for money |
| Never trust client-reported usage alone | Server measures |

## Stripe setup (sketch)

1. Product + **metered** price (or Billing Meter in current Stripe API)
2. Customer + subscription with that item
3. Server reports usage against `subscription_item` / meter
4. Stripe aggregates and invoices each period

```typescript
// Illustrative - match current Stripe SDK for your API version
import "server-only";
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function reportMeteredUsage(opts: {
 subscriptionItemId: string;
 quantity: number;
 idempotencyKey: string;
 timestamp?: number;
}) {
 // Prefer modern Meters API when on newer Stripe Billing;
 // legacy: subscriptionItems.createUsageRecord
 await stripe.subscriptionItems.createUsageRecord(
 opts.subscriptionItemId,
 {
 quantity: opts.quantity,
 timestamp: opts.timestamp ?? Math.floor(Date.now() / 1000),
 action: "increment",
 },
 { idempotencyKey: opts.idempotencyKey },
 );
}
```

Pin API version in the Stripe client; re-read Stripe docs when upgrading SDK (meter APIs evolve).

## Local quota (UX + abuse)

```sql
create table public.usage_counters (
 org_id uuid not null references public.orgs (id) on delete cascade,
 meter text not null,
 period_start date not null,
 quantity bigint not null default 0,
 primary key (org_id, meter, period_start)
);

alter table public.usage_counters enable row level security;
-- members can read own org counters; only server increments
```

```typescript
export async function assertWithinQuota(orgId: string, meter: string, add: number) {
 const { used, limit } = await getQuota(orgId, meter);
 if (used + add > limit) {
 throw new QuotaExceededError({ meter, used, limit });
 }
}
```

- Soft limit: show banner at 80%
- Hard limit: fail Server Action with upgrade CTA
- Entitlements from plan table; never client-only

## Webhooks

| Event | Action |
|---|---|
| `invoice.paid` | Clear past_due; reset soft-lock UX |
| `invoice.payment_failed` | past_due; dunning email (`email-notifications.md`) |
| `customer.subscription.updated` | Sync metered items / price changes |

Idempotent handlers: `backend-webhooks.md`.

## Testing

- Unit: quota math, idempotency key stable per event id
- Integration: mock Stripe; assert one usage report per job retry
- Never hit live Stripe in default CI

## Anti-patterns

- Client sends `quantity` without server measurement
- Reporting usage in the request path without retry/idempotency
- Conflating **seat quantity** with **usage meters**
- Unlocking paid overage on `?success=true`
- No hard limit (runaway cost / abuse)
- Logging full Stripe payloads with PII

## Related

- `billing-stripe.md` - Checkout, Portal, entitlements
- `billing-seats.md` - seat quantity sync
- `backend-webhooks.md` - signatures + idempotency
- `background-jobs.md` - durable report workers
- `email-notifications.md` - dunning
- `ai-boundary.md` - token/API usage meters for AI products

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
