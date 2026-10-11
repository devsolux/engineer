# Backend webhooks: Stripe, idempotency, Edge Functions

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

Inbound webhooks are untrusted until verified. Process fast, side effects safely.

Delegate `/cso` before shipping payment or auth-adjacent webhooks.

## Contents
- [Enforcement](#enforcement)
- [Inbound webhook flow](#inbound-webhook-flow)
- [Stripe webhook (Route Handler)](#stripe-webhook-route-handler)
- [Idempotency](#idempotency)
- [Subscription state sync](#subscription-state-sync)
- [Outbound events (app → workers)](#outbound-events-app--workers)
- [Supabase Edge Functions](#supabase-edge-functions)
- [Other webhook providers](#other-webhook-providers)
- [Enforcement](#enforcement-1)
- [Anti-patterns](#anti-patterns)

## Enforcement

| Rule | Tool |
|---|---|
| Raw body before verify | `engineer-scan` warns on `req.json()` in webhooks |
| Idempotency | Unit test: duplicate event.id → no double write |
| Signature | Stripe CLI trigger in CI/staging |
| Secrets | gitleaks; never in client bundle |

See `enforcement-rules.md` § rule → enforcement map (webhook signature).

## Inbound webhook flow

```
POST /api/webhooks/stripe
 → read raw body (required for signature)
 → verify signature
 → parse + Zod validate event shape
 → idempotency check (event.id)
 → process or enqueue
 → return 200 quickly
```

## Stripe webhook (Route Handler)

```typescript
// app/api/webhooks/stripe/route.ts
import Stripe from "stripe";
import { headers } from "next/headers";
import { stripe } from "@/lib/stripe/server";
import { processStripeEvent } from "@/lib/stripe/handlers";

export async function POST(req: Request) {
 const body = await req.text(); // raw body - not req.json() first
 const signature = (await headers()).get("stripe-signature");

 if (!signature) {
 return Response.json({ error: "Missing signature" }, { status: 400 });
 }

 let event: Stripe.Event;
 try {
 event = stripe.webhooks.constructEvent(
 body,
 signature,
 process.env.STRIPE_WEBHOOK_SECRET!
 );
 } catch {
 return Response.json({ error: "Invalid signature" }, { status: 400 });
 }

 try {
 await processStripeEvent(event); // idempotent inside
 } catch (err) {
 // Log; return 500 so Stripe retries
 console.error("Webhook processing failed", err);
 return Response.json({ error: "Processing failed" }, { status: 500 });
 }

 return Response.json({ received: true });
}
```

Rules:
- **Raw body** for signature verification
- **Webhook secret** from env - never client-exposed
- Return **500** on processing failure (Stripe retries)
- Return **400** on bad signature (don't retry junk)
- Handle events you subscribe to; ignore unknown types safely

## Idempotency

Stripe may deliver the same event more than once. Dedupe on `event.id`:

```typescript
// lib/stripe/handlers.ts
export async function processStripeEvent(event: Stripe.Event) {
 const supabase = createAdminClient(); // service role - server only

 const { data: existing } = await supabase
 .from("stripe_events")
 .select("id")
 .eq("event_id", event.id)
 .maybeSingle();

 if (existing) return; // already processed

 await supabase.from("stripe_events").insert({
 event_id: event.id,
 type: event.type,
 });

 switch (event.type) {
 case "checkout.session.completed":
 await handleCheckoutCompleted(event);
 break;
 // ...
 }
}
```

Alternative: Redis `SET event.id NX EX 86400` for short TTL lock.

For Stripe **API calls** (not webhooks), pass `idempotencyKey` on mutating requests.

## Subscription state sync

```
checkout.session.completed → create/update subscription row
customer.subscription.updated → sync status, period_end
customer.subscription.deleted → mark canceled
invoice.payment_failed → notify + grace period logic
```

Single source of truth: Stripe for billing state; Supabase for app entitlements.
Sync via webhooks - don't poll Stripe from client.

## Outbound events (app → workers)

For heavy processing:

1. Webhook handler validates + stores event + enqueues job
2. Worker (Edge Function, Rust, cron) processes with retry
3. Dead letter queue for failed jobs after N retries

Return 200 from webhook before heavy work when using async queue.

## Supabase Edge Functions

Use when:
- Scheduled jobs (pg_cron + invoke)
- Isolation from Next.js runtime
- Webhook receiver closer to Supabase DB
- Non-Node runtimes

```typescript
// supabase/functions/process-job/index.ts
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

Deno.serve(async (req) => {
 const authHeader = req.headers.get("Authorization");
 // Verify service token or signed payload - never open endpoint

 const supabase = createClient(
 Deno.env.get("SUPABASE_URL")!,
 Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
 );

 // ... job logic
 return new Response(JSON.stringify({ ok: true }), {
 headers: { "Content-Type": "application/json" },
 });
});
```

Rules:
- Verify caller (JWT, shared secret, Supabase signed request)
- Service role in Edge Function env only - never in client bundle
- CORS locked if browser-accessible (prefer server-to-server)

## Other webhook providers

Same pattern:
- Verify signature (provider-specific)
- Zod validate payload subset you use
- Idempotency on provider event ID
- 200 fast; async for heavy work

## Enforcement

| Rule | Tool |
|---|---|
| Raw body before verify | `engineer-scan` warns on `req.json()` in webhooks |
| Idempotency | Unit test: duplicate event.id → no double write |
| Signature | Stripe CLI trigger in CI/staging |
| Secrets | gitleaks; never in client bundle |

Delegate gstack `/cso` before shipping payment webhooks. See `enforcement.md`.

## Anti-patterns

- `req.json()` before Stripe signature verify (breaks HMAC)
- No idempotency (double charges, duplicate emails)
- 200 on processing failure (Stripe won't retry)
- Service role key in Edge Function exposed to browser
- Syncing subscription state from client Stripe calls
- Webhook endpoint with no auth/signature verification
- Storing full card data (PCI - use Stripe Elements/Checkout)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
