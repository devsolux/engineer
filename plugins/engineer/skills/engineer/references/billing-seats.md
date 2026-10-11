# Seat billing (org quantity)

**Last verified**: 2026-07-13 · **Review cadence**: 3 months

Org-level Stripe seats tied to **membership counts**. Requires
`backend-multitenant.md` + `billing-stripe.md` + webhook unlock discipline.
Pricing-model fit (seat vs usage vs outcome, packaging, WTP) is business-knowledge reference-skill
`pricing-monetization` knowledge; this module implements the chosen model.

## Model

```
org → stripe_customer_id
org → subscription (quantity = paid seats)
memberships (active) ≤ paid seats (or soft-warn overage)
```

| Field | Source of truth |
|---|---|
| Who is in the org | `memberships` table |
| Who pays | Stripe customer on **org** |
| How many seats paid | Subscription `quantity` (webhook-synced) |

## Checkout quantity

```typescript
// create checkout for org plan with seat quantity
const members = await countActiveMembers(orgId);
const quantity = Math.max(members, 1);

const session = await stripe.checkout.sessions.create({
 mode: "subscription",
 customer: org.stripeCustomerId,
 line_items: [{ price: SEAT_PRICE_ID, quantity }],
 subscription_data: {
 metadata: { org_id: orgId },
 },
 success_url: `${origin}/billing?ok=1`,
 cancel_url: `${origin}/billing`,
 // NEVER unlock access from success_url alone
});
```

## Webhook → entitlement

On `customer.subscription.updated` / `created`:

1. Read `metadata.org_id` (or map customer → org)
2. Upsert `subscriptions` row: status, price_id, **quantity**, period end
3. Optional: job to email owner if members > quantity

```sql
-- example entitlement columns on subscriptions
alter table public.subscriptions
 add column if not exists org_id uuid references public.orgs (id),
 add column if not exists quantity int not null default 1;
```

## Invite gate

```typescript
export async function inviteMember(orgId: string, email: string) {
 await requireOrgAdmin(orgId);
 await rateLimit(orgId); // abuse
 const { members, seats } = await getSeatUsage(orgId);
 if (members >= seats) {
 return { error: "seat_limit", seats };
 }
 // create invite...
 await writeAudit({ orgId, actorId, action: "member.invite", ... });
}
```

| Policy | When |
|---|---|
| Hard block invite | Default SaaS |
| Soft overage + invoice | Enterprise custom |
| Auto-increase quantity | Portal + proration (careful UX) |

## Portal

- Billing Portal session for **org owner / billing role** only
- Quantity changes via Portal or in-app “add seats” → Checkout/update subscription API
- Always re-read quantity from webhook-updated DB

## Anti-patterns

- Seats on **user** while product is org-based
- Unlocking seats from success_url
- Counting deleted/soft-left members as active seats forever
- No rate limit on invite storm

## Ship checklist

- [ ] Customer + subscription on org
- [ ] quantity synced via webhook
- [ ] invite blocked at limit (or documented overage)
- [ ] owner/billing role only manages plan
- [ ] audit log on seat changes / invites
- [ ] gstack cso pass before production money path

## Related

- `billing-stripe.md` · `backend-webhooks.md` · `backend-multitenant.md`
- `audit-log.md` · `background-jobs.md` · `composition.md` (cso)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
