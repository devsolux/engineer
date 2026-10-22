# Multi-tenant orgs: memberships, roles, invites

**Last verified**: 2026-10-22 · **Review cadence**: 6 months

SaaS default: **org (workspace) + memberships + roles**. Complements
`backend-auth.md` (identity), `backend-database.md` (RLS), `billing-stripe.md`
(seats/plans).

Research: `research/deep-2026-07.md` · Gaps: `research/gap-audit.md`

## Contents
- [Model](#model)
- [Roles](#roles)
- [Invites](#invites)
- [RLS patterns](#rls-patterns)
- [Transfer and offboarding](#transfer-and-offboarding)
- [Billing handoff](#billing-handoff)
- [Anti-patterns](#anti-patterns)
- [Ship checklist](#ship-checklist)

## Model

```
users ──< memberships >── orgs
 │
 role: owner | admin | member | billing
```

| Table | Notes |
|---|---|
| `orgs` | id, name, slug, created_at |
| `memberships` | org_id, user_id, role, unique(org_id, user_id) |
| `invites` | org_id, email, role, token_hash, expires_at, accepted_at |

Prefer **membership row** as the tenancy primitive. Avoid “current org” only in JWT without a membership check.

## Roles

| Role | Typical powers |
|---|---|
| `owner` | Transfer ownership, delete org, manage billing |
| `admin` | Invite/remove members, manage resources |
| `member` | Create/edit own resources; read org shared data |
| `billing` | Optional: invoices only |

Keep roles few. Fine-grained permissions later via capabilities table if needed.

## Invites

1. Admin creates invite → store **hash** of token, not raw token
2. Email link with raw token (short TTL, e.g. 7 days)
3. Accept: verify hash + expiry + email match → insert membership → mark accepted
4. Race: unique(org_id, user_id) prevents double membership

**Never** accept invites without auth of the accepting user (or explicit email magic-link bind).

## RLS patterns

```sql
-- helper: is member of org (private schema, not exposed to the Data API)
create or replace function private.is_org_member(p_org uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
 select exists (
 select 1 from public.memberships m
 where m.org_id = p_org and m.user_id = (select auth.uid())
 );
$$;
revoke all on function private.is_org_member(uuid) from public;
grant usage on schema private to authenticated;
grant execute on function private.is_org_member(uuid) to authenticated;

-- example resource policy
create policy "org members read projects"
on public.projects for select
to authenticated
using (private.is_org_member(org_id));
```

Rules:

- `SECURITY DEFINER` helpers: non-exposed schema, `search_path = ''` + schema-qualified names, membership check only
- Session-variable tenancy (`set_config('app.org_id', …, true)` read via `current_setting`) stays transaction-local; session `SET` is unsafe under transaction pooling (Supavisor/PgBouncer)
- Never trust `org_id` from the client without membership
- Service role only in workers/admin jobs (`background-jobs.md`)

## Transfer and offboarding

| Event | Action |
|---|---|
| Owner transfer | Two-step: nominate + accept; ensure ≥1 owner always |
| Member leave | Delete membership; reassign or soft-delete owned rows |
| User delete (GDPR) | See `compliance-privacy.md` - export then purge memberships |

## Billing handoff

- Stripe customer usually on **org**, not user
- Seat counts from active memberships
- Only owner/billing can change plan
- Webhook updates org subscription state → jobs for seat enforcement

Deep billing: `billing-stripe.md`.

## Anti-patterns

- Org id in cookie with no membership re-check
- Soft-delete membership but leave wide RLS
- Invites that never expire
- Single global admin that bypasses org RLS in app code
- Mixing personal workspace and team org without clear product rule

## Ship checklist

- [ ] orgs + memberships + roles in schema
- [ ] RLS uses membership helpers
- [ ] Invite token hashed + TTL + accept race safe
- [ ] Owner transfer keeps ≥1 owner
- [ ] Billing role / seat source documented
- [ ] Offboarding path for leave + user delete

## Related

- `backend-auth.md` - session identity
- `backend-database.md` - RLS discipline
- `billing-stripe.md` - seats and customers
- `compliance-privacy.md` - export/delete
- `background-jobs.md` - async seat/sync work
