# Admin / support access patterns

**Last verified**: 2026-07-14 · **Review cadence**: 3 months

Staff support, superuser reads, and optional impersonation for SaaS apps.
Load with `backend-auth.md`, `backend-multitenant.md`, `audit-log.md`,
`backend-security.md`, `compliance-privacy.md`.

## Goals

- Support can diagnose customer issues without sharing passwords
- Every elevated action is **audited**
- Break-glass access is time-boxed and least-privilege
- Product RLS remains the default path for normal users

## Role model (minimal)

| Role | Who | Power |
|---|---|---|
| `user` | Customer | Own org data via membership RLS |
| `support` | Staff | Read (and limited write) via **explicit** admin policies or service tools |
| `admin` | Internal superuser | Broader staff tools; still audited |

Store staff roles **outside** customer `memberships` (e.g. `staff_users` table or private claim issued only by your backend). Never put `is_admin` on the client alone.

## Patterns (pick one primary)

### A. Separate admin app / service role tools (preferred for early SaaS)

```text
Support UI (VPN or staff SSO)
 -> staff-only Server Actions
 -> service_role or SECURITY DEFINER helpers
 -> audit_log every access
 -> never ship service_role to the browser
```

- Customer app keeps strict RLS
- Support tools live in a **separate route group** or app (`/admin`) with staff auth
- Query by `org_id` / `user_id` with explicit allowlist of tables

### B. Impersonation (session-as-user)

Use only when product workflows must be seen as the customer.

```text
staff authenticates
 -> start_impersonation(target_user_id, reason, ttl)
 -> audit_log: impersonation.start
 -> short-lived session / claim with target subject
 -> all product queries use normal RLS as target
 -> end_impersonation -> audit_log: impersonation.end
```

| Rule | Why |
|---|---|
| Require **reason** string | Accountability |
| Hard **TTL** (e.g. 15-30 min) | Limits blast radius |
| Banner in UI "Viewing as …" | Prevent silent confusion |
| Block billing mutations unless second factor | Money safety |
| Log start/end + target + staff id | Forensics |
| Always-ask risk gate for agents | workflows.md |

### C. Break-glass read policies

Rare SQL policies for `staff_users` role:

```sql
-- illustrative - keep policies narrow and reviewed
create policy "staff read tickets"
 on public.tickets for select
 using (
 public.is_org_member(org_id)
 or public.is_staff('support')
 );
```

Prefer pattern A over spraying `or is_staff()` across every table.

## Audit requirements

Every elevated path writes to `audit_log` (see `audit-log.md`):

| Event | Fields |
|---|---|
| `impersonation.start` / `.end` | staff_id, target_user_id, reason, ip |
| `admin.read` | resource type/id, staff_id |
| `admin.write` | before/after or diff summary (no secrets) |

Retention: long enough for support disputes; redact PII per privacy policy.

## Auth implementation notes

- Staff SSO (Google Workspace / SAML) beats shared passwords
- Middleware: `/admin/*` requires staff claim; customer JWT insufficient
- Rotate break-glass credentials; store in secret manager
- Agents: **always-ask** before implementing impersonation or service_role UI

## Testing

| Case | Expect |
|---|---|
| Normal user hits `/admin` | 401/403 |
| Support without reason starts impersonation | rejected |
| Impersonation expired | back to staff session |
| Support read of org B as user A | denied |
| Audit rows exist for start/end | assert in tests |

## Anti-patterns

- `service_role` in a Client Component "admin page"
- Permanent impersonation cookies without TTL
- Silent impersonation (no UI banner)
- `is_admin` boolean on `profiles` writable by the user
- Skipping audit logs "just for support"
- Agent auto-enabling cross-tenant select policies without review

## Related

- `audit-log.md` - event schema and RLS
- `backend-auth.md` - session model
- `backend-multitenant.md` - membership boundaries
- `compliance-privacy.md` - access to personal data
- `workflows.md` - always-ask risk class
- `ai-security.md` - tools that must not use service_role casually

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
