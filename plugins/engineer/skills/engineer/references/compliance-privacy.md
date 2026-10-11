# Compliance & privacy: engineering checklist

**Last verified**: 2026-07-14 · **Review cadence**: 6 months

**Not legal advice.** Engineering controls for GDPR-style privacy requirements.
App security: `backend-security.md`. Email: `email-notifications.md`.
Admin access: `backend-admin.md`. Jobs: `background-jobs.md`.

Legal review required for jurisdiction-specific obligations (CCPA, UK GDPR, etc.).

## Contents
- [Scope: what engineering owns](#scope-what-engineering-owns)
- [Data inventory (do first)](#data-inventory-do-first)
- [Retention (engineering)](#retention-engineering)
- [User rights - implementation patterns](#user-rights---implementation-patterns)
- [Consent](#consent)
- [Security controls (privacy-adjacent)](#security-controls-privacy-adjacent)
- [Breach preparedness (engineering)](#breach-preparedness-engineering)
- [Checklist before EU launch](#checklist-before-eu-launch)
- [Anti-patterns](#anti-patterns)
- [Composition](#composition)

## Scope: what engineering owns

| Engineering | Legal / DPO |
|---|---|
| Data export API | Privacy policy text |
| Delete account flow | Cookie banner copy |
| Consent storage | DPA with vendors |
| Audit logs | Lawful basis documentation |
| RLS + encryption in transit | Records of processing |
| Retention jobs | Retention policy wording |

## Data inventory (do first)

Document in `docs/privacy/data-inventory.md` (or internal wiki):

| Data | Table/storage | Purpose | Retention | Third parties |
|---|---|---|---|---|
| Email | auth.users | Auth | Until delete | Supabase |
| Projects | public.projects | Product | Until delete | - |
| Avatars | storage.avatars | Profile | Until delete | Supabase CDN |
| Usage meters | public.usage_counters | Billing UX | Period + N days | Stripe |
| Support notes | admin systems | Support | Policy-defined | - |

Update when adding tables, analytics, email providers, RAG corpora, or AI logs.

## Retention (engineering)

| Class | Typical approach | Job |
|---|---|---|
| Account data | Until user delete / contract end | delete-account cascade |
| App logs | 14-90 days | log sink retention |
| AI prompts/traces | Short + redacted; or opt-in | trace scrub job |
| Backups | Document restore window | vendor settings |
| Soft-deleted rows | Purge after N days | scheduled purge |

Write retention as code comments + runbook, not only a Notion page.

## User rights - implementation patterns

### Access / export (Article 15 / portability)

Server Action or Route Handler - auth required:

```
getUser()
 -> rate limit
 -> if small: sync JSON download
 -> if large: enqueue export job + email signed URL
 -> audit_log: privacy.export.requested / .completed
```

```typescript
export async function exportUserData() {
 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) throw new Error("Unauthorized");

 const [profile, projects, files] = await Promise.all([
 supabase.from("profiles").select("*").eq("id", user.id).single(),
 supabase.from("projects").select("*").eq("user_id", user.id),
 supabase.from("files").select("*").eq("user_id", user.id),
 ]);

 return {
 exportedAt: new Date().toISOString(),
 userId: user.id,
 profile: profile.data,
 projects: projects.data,
 files: files.data,
 };
}
```

Rules:
- Rate-limit exports (abuse + cost)
- Do not include **other users'** rows (RLS + explicit filters)
- Signed URLs for files: short TTL
- Large exports: durable job (`background-jobs.md`)
- Engineering SLA: aim to complete automated export quickly; legal response timelines are legal's call - build queues so you are not blocked on a human zip

### Erasure / delete account (Article 17)

Order matters (partial delete is worse than none):

```
1. Re-auth (password or step-up)
2. Cancel Stripe subscription (billing-stripe.md)
3. Revoke sessions / API keys
4. Delete storage objects (backend-storage.md)
5. Delete public.* rows (FK cascade or explicit order)
6. Delete auth.users via Admin API (service role, server-only job)
7. Anonymize analytics / support tickets if full delete not possible (document residual)
8. audit_log: privacy.delete.completed (without re-storing PII)
```

Use an **idempotent durable job** with a status row (`delete_jobs`: pending/running/done/failed).

```typescript
// Server-only admin client
async function deleteAccount(userId: string) {
 await cancelStripeForUser(userId);
 await deleteUserStorage(userId);
 await admin.from("profiles").delete().eq("id", userId);
 // ... cascade tables from data inventory
 await admin.auth.admin.deleteUser(userId);
}
```

UI: clear copy that delete is irreversible; optional grace period is a product/legal choice.

### Rectification

Standard profile update flows - `backend-api.md`.
Audit trail if regulated industry.

### DSAR queue (when not fully self-serve)

```sql
create table public.privacy_requests (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null,
 kind text not null check (kind in ('export', 'delete', 'other')),
 status text not null default 'received',
 created_at timestamptz not null default now(),
 completed_at timestamptz
);
-- staff-only read/write via admin tools; user can insert own request
```

Staff playbook: `backend-admin.md` + audit every access.

## Consent

### Marketing email

- Separate opt-in from Terms of Service
- Store `marketing_consent_at`, `marketing_consent_version` on profile
- Unsubscribe link in every marketing email (`email-notifications.md`)
- Do not pre-check marketing boxes

### Analytics

- Load analytics only after consent if EU traffic (or use cookieless analytics)
- Document in privacy policy
- Provide opt-out in settings

### Cookie banner

Engineering provides:
- Consent state in cookie/localStorage
- Conditional script loading in layout
- Link to cookie preferences page

Copy and legal basis: legal team.

## Security controls (privacy-adjacent)

Cross-ref `backend-security.md`:
- TLS everywhere
- RLS on all user data
- No PII in logs (mask email in structured logs)
- Short retention on server logs
- DPA-signed subprocessors (Supabase, Stripe, Resend, Sentry)

## Breach preparedness (engineering)

- Error tracking with PII scrubbing (Sentry `beforeSend`)
- Runbook: who disables compromised keys, notification timeline
- Service role key rotation procedure in `deploy-ops.md`

## Checklist before EU launch

- [ ] Data inventory documented (includes AI logs / RAG if any)
- [ ] Privacy policy + ToS linked in footer and signup
- [ ] Export data flow tested (small + large path)
- [ ] Delete account flow tested end-to-end (Stripe + storage + auth)
- [ ] Marketing consent separate and stored
- [ ] Cookie/analytics consent if required
- [ ] Subprocessor list current
- [ ] Retention jobs configured for logs/traces
- [ ] RLS verified on all PII tables (pgTAP - `backend-testing.md`)
- [ ] Legal review completed

## Anti-patterns

| Don't | Do |
|---|---|
| Hard delete without Stripe cancel | Ordered teardown |
| Export includes other users' data | Strict RLS + getUser() |
| PII in Sentry breadcrumbs | Scrub beforeSend |
| "Delete" that only disables UI | Backend + auth delete |
| One checkbox for ToS + marketing | Separate consents |
| Infinite retention "just in case" | Defined retention per data class |
| Sync export of multi-GB accounts in a Server Action | Durable job + signed URL |
| Staff viewing exports without audit | `backend-admin.md` + audit_log |

## Composition

| Module | When |
|---|---|
| `backend-storage.md` | Delete user files |
| `billing-stripe.md` | Cancel subscription on delete |
| `billing-metered.md` | Usage counters teardown |
| `backend-auth.md` | Re-auth before delete |
| `backend-admin.md` | Staff DSAR handling |
| `ai-security.md` | Prompt/trace retention |
| `frontend-i18n.md` | Localized privacy copy |
| `email-notifications.md` | Unsubscribe + transactional vs marketing |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
