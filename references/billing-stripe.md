# Billing: Stripe Checkout, Portal, entitlements

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Full subscription billing - not just webhooks (`backend-webhooks.md`).
Webhooks sync state; this module covers purchase flow and access control.

**Default API:** Stripe [Checkout Sessions](https://docs.stripe.com/payments/checkout-sessions-and-payment-intents-comparison) for hosted or Payment-Element-on-Checkout flows. Use PaymentIntents directly only when the product owns a custom checkout. Pin **one** Stripe API version per app (the Stripe SDK default is fine; do not mix versions). Never unlock on `success_url`.

**Org seats / quantity:** see **`billing-seats.md`** (membership count → Stripe quantity).
**Usage / overage meters:** see **`billing-metered.md`** (API calls, tokens, storage).

Delegate gstack `/cso` before ship.

## Contents
- [Architecture](#architecture)
- [Data model](#data-model)
- [Checkout Session (Server Action)](#checkout-session-server-action)
- [Customer Portal](#customer-portal)
- [Entitlements (access control)](#entitlements-access-control)
- [Webhook events (minimum set)](#webhook-events-minimum-set)
- [Pricing page UI](#pricing-page-ui)
- [Anti-patterns](#anti-patterns)

## Architecture

```
Pricing UI → Server Action creates Checkout Session
 → User pays on Stripe-hosted Checkout
 → Webhook updates DB (source of truth)
 → App reads entitlements from DB (not Stripe API per request)

Billing settings → Customer Portal session → Stripe-hosted management
```

**Never unlock on `success_url` query params.** Webhooks only.

## Data model

```sql
create table public.subscriptions (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users (id) on delete cascade,
 stripe_customer_id text not null,
 stripe_subscription_id text unique,
 status text not null, -- active, trialing, past_due, canceled, ...
 price_id text not null,
 current_period_end timestamptz,
 cancel_at_period_end boolean default false,
 created_at timestamptz default now(),
 updated_at timestamptz default now()
);

alter table public.subscriptions enable row level security;

create policy "Users read own subscription"
 on public.subscriptions for select
 to authenticated
 using ((select auth.uid()) = user_id);

create table public.stripe_events (
 event_id text primary key,
 type text not null,
 processed_at timestamptz default now()
);
```

Service role writes subscriptions via webhook handler - not user INSERT.

## Checkout Session (Server Action)

```typescript
"use server";

import Stripe from "stripe";
import { createClient } from "@/lib/supabase/server";
import { PLANS } from "@/lib/billing/plans";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!); // pin apiVersion in one module, not per call

export async function createCheckoutSession(planKey: string) {
 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { ok: false as const, error: "Unauthorized" };

 const plan = PLANS[planKey];
 if (!plan) return { ok: false as const, error: "Invalid plan" };

 // Get or create Stripe customer - store stripe_customer_id on profile
 const customerId = await getOrCreateStripeCustomer(user.id, user.email!);

 const session = await stripe.checkout.sessions.create({
 mode: "subscription",
 customer: customerId,
 line_items: [{ price: plan.priceId, quantity: 1 }],
 success_url: `${process.env.NEXT_PUBLIC_BASE_URL}/dashboard?checkout=success`,
 cancel_url: `${process.env.NEXT_PUBLIC_BASE_URL}/pricing`,
 subscription_data: plan.trialDays
 ? { trial_period_days: plan.trialDays }
 : undefined,
 metadata: { userId: user.id },
 });

 return { ok: true as const, url: session.url! };
}
```

Config-driven plans:

```typescript
// lib/billing/plans.ts
export const PLANS = {
 pro: { priceId: process.env.STRIPE_PRICE_PRO!, trialDays: 14 },
 team: { priceId: process.env.STRIPE_PRICE_TEAM! },
} as const;
```

## Customer Portal

```typescript
"use server";

export async function createPortalSession() {
 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { ok: false as const, error: "Unauthorized" };

 const customerId = await getStripeCustomerId(user.id);
 if (!customerId) return { ok: false as const, error: "No subscription" };

 const session = await stripe.billingPortal.sessions.create({
 customer: customerId,
 return_url: `${process.env.NEXT_PUBLIC_BASE_URL}/settings/billing`,
 });

 return { ok: true as const, url: session.url };
}
```

Configure Portal in Stripe Dashboard - don't build custom plan management unless required.

## Entitlements (access control)

```typescript
// lib/billing/entitlements.ts
import "server-only";

export async function getEntitlements(userId: string) {
 const sub = await getSubscriptionFromDb(userId);
 return {
 canUseFeatureX: sub?.status === "active" || sub?.status === "trialing",
 plan: sub?.price_id ?? "free",
 isPastDue: sub?.status === "past_due",
 };
}
```

Check entitlements in Server Components / Actions - never client-only gating for paid features.

Feature gate UI:

```tsx
const { canUseFeatureX } = await getEntitlements(user.id);
if (!canUseFeatureX) return <UpgradePrompt feature="Feature X" />;
```

## Webhook events (minimum set)

| Event | Action |
|---|---|
| `checkout.session.completed` | Link customer, create subscription row |
| `customer.subscription.updated` | Sync status, price, and period end from the subscription item (`items.data[].current_period_end` since `2025-03-31.basil`) |
| `customer.subscription.deleted` | Mark canceled |
| `invoice.payment_failed` | Mark past_due, notify user |

Full handler patterns: `backend-webhooks.md`.

## Pricing page UI

See `conversion-ui.md`. Billing-specific:
- 3 tiers max; recommended badge
- Annual toggle with savings %
- CTA → `createCheckoutSession(planKey)`
- FAQ: cancel, refund, export

## Anti-patterns

- Unlock on success redirect
- Query Stripe API on every page load for access
- Custom billing UI when Portal suffices
- No idempotency on webhook handler
- Storing card data (PCI - use Stripe Elements/Checkout)
- Missing past_due / failed payment UX

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
