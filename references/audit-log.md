# Audit log pattern (B2B / compliance)

**Last verified**: 2026-07-13 · **Review cadence**: 3 months

Append-only activity trail for security-sensitive actions. Complements
`backend-multitenant.md`, `compliance-privacy.md`, `background-jobs.md`.

## When required

| Trigger | Examples |
|---|---|
| B2B / SOC2-ish | member invite, role change, export, delete |
| Money | plan change, seat purchase, refund initiate |
| Admin | impersonation start/stop, feature flag override (see `backend-admin.md`) |

Skip for pure content reads unless regulated industry.

## Schema

```sql
create table public.audit_events (
 id uuid primary key default gen_random_uuid(),
 org_id uuid not null references public.orgs (id) on delete cascade,
 actor_id uuid references auth.users (id) on delete set null,
 action text not null, -- 'member.invite' | 'export.request' | ...
 entity_type text, -- 'membership' | 'project' | ...
 entity_id text,
 metadata jsonb not null default '{}',
 ip inet,
 user_agent text,
 created_at timestamptz not null default now()
);

create index audit_events_org_created on public.audit_events (org_id, created_at desc);

alter table public.audit_events enable row level security;

-- members can read org audit trail (or restrict to admin)
create policy "org admins read audit"
on public.audit_events for select
using (
 exists (
 select 1 from public.memberships m
 where m.org_id = audit_events.org_id
 and m.user_id = auth.uid()
 and m.role in ('owner', 'admin')
 )
);

-- no update/delete for authenticated roles (append-only)
-- inserts via service role or SECURITY DEFINER writer after authz
```

## Write path

```typescript
// lib/audit.ts - call AFTER successful authz, never as the only auth check
export async function writeAudit(event: {
 orgId: string;
 actorId: string;
 action: string;
 entityType?: string;
 entityId?: string;
 metadata?: Record<string, unknown>;
}) {
 const admin = createServiceClient(); // server only
 await admin.from("audit_events").insert({
 org_id: event.orgId,
 actor_id: event.actorId,
 action: event.action,
 entity_type: event.entityType,
 entity_id: event.entityId,
 metadata: event.metadata ?? {},
 });
}
```

| Rule | Practice |
|---|---|
| Append-only | No UPDATE/DELETE policies for app roles |
| Least data | Store ids + action; avoid full PII payloads |
| Fail open vs closed | Prefer fail-open log (don't block UX) unless compliance requires fail-closed |
| Async | High-volume paths: enqueue (`background-jobs.md`) |

## Retention

- Default: 1-2 years hot, then cold storage or delete job
- GDPR user delete: scrub `actor_id` / metadata fields; keep org integrity rows if legal basis holds
- Job: nightly prune via durable worker

## Anti-patterns

- Client-writable audit table
- Logging secrets or full request bodies
- Using audit as authorization
- No index on `(org_id, created_at)`

## Ship checklist

- [ ] Schema + RLS + append-only grants
- [ ] Writer only on server after authz
- [ ] Critical actions instrumented (invite, role, export, billing)
- [ ] Retention job documented
- [ ] Admin UI read path rate-limited

## Related

- `backend-multitenant.md` · `compliance-privacy.md` · `background-jobs.md` · `billing-stripe.md`

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
