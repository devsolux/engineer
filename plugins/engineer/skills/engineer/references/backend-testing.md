# Backend testing: RLS, actions, and integration

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

Database and server integration tests beyond frontend RTL/Playwright.
Frontend tests: `frontend-testing.md`. CI wiring: `enforcement.md`.

## Contents
- [Test pyramid (backend)](#test-pyramid-backend)
- [pgTAP + Supabase CLI](#pgtap-supabase-cli)
- [pgTAP patterns](#pgtap-patterns)
- [RLS test matrix (per table)](#rls-test-matrix-per-table)
- [Server Action tests (Vitest)](#server-action-tests-vitest)
- [Route Handler / webhook tests](#route-handler-webhook-tests)
- [Migration gate script](#migration-gate-script)
- [What to test when](#what-to-test-when)
- [Anti-patterns](#anti-patterns)
- [Composition](#composition)

## Test pyramid (backend)

```
 E2E (Playwright) - critical auth + payment flows
 / \
 Integration - Server Actions, Route Handlers, webhooks
 / \
pgTAP RLS - every table + storage policy
Unit (Vitest) - Zod schemas, pure helpers
```

**Hard gate**: new `public` table or storage bucket → pgTAP test in same PR.

## pgTAP + Supabase CLI

### Layout

```
supabase/
 migrations/
 tests/
 rls_projects.test.sql
 rls_storage_avatars.test.sql
 helpers.sql # optional fixtures
```

### Run locally

```bash
supabase start
supabase db reset
supabase test db
```

### CI (from enforcement-rules.md)

```yaml
- uses: supabase/setup-cli@v1
- run: supabase start
- run: supabase db reset
- run: supabase test db
```

Template: `templates/supabase/tests/rls_projects.test.sql`

## pgTAP patterns

### Test anon cannot read protected data

```sql
begin;
select plan(2);

set local role anon;

select is(
 (select count(*)::int from public.projects),
 0,
 'anon sees zero projects'
);

select finish();
rollback;
```

### Test authenticated isolation

Use Supabase test helpers or manual JWT simulation:

```sql
begin;
select plan(3);

-- Create two users via auth.users (test fixture)
-- Set request.jwt.claim.sub for user A
-- Insert project as A
-- Assert B cannot select A's row

select finish();
rollback;
```

Prefer **`supabase test db`** fixtures over testing against production.

### Storage RLS

```sql
begin;
select plan(2);

set local role authenticated;
-- set jwt claim to user id

select throws_ok(
 $$ insert into storage.objects (bucket_id, name, owner, metadata)
 values ('avatars', 'other-user-id/photo.png', auth.uid(), '{}'::jsonb) $$,
 'new row violates row-level security policy',
 'cannot upload to another user folder'
);

select finish();
rollback;
```

## RLS test matrix (per table)

| Case | Expect |
|---|---|
| anon SELECT | deny or empty |
| authenticated SELECT own | allow |
| authenticated SELECT other | deny |
| authenticated INSERT own | allow |
| authenticated INSERT other user_id | deny |
| authenticated UPDATE own | allow |
| authenticated UPDATE other | deny |
| authenticated DELETE own | allow |
| service_role | bypass (document why in code review) |

Document matrix in PR when adding policies.

## Server Action tests (Vitest)

Test the **validation and auth branches** without full Next runtime when possible:

```typescript
import { describe, it, expect, vi } from "vitest";
import { createProjectSchema } from "./schema";

describe("createProjectSchema", () => {
 it("rejects empty name", () => {
 expect(createProjectSchema.safeParse({ name: "" }).success).toBe(false);
 });
});
```

Integration with mocked Supabase:

```typescript
vi.mock("@/lib/supabase/server", () => ({
 createClient: vi.fn(() => ({
 auth: { getUser: vi.fn().mockResolvedValue({ data: { user: null } }) },
 })),
}));

it("returns unauthorized when no user", async () => {
 const result = await createProject({ name: "Test" });
 expect(result.error).toMatch(/unauthorized/i);
});
```

For full Action integration, use `@playwright/test` against running dev server.

## Route Handler / webhook tests

Stripe webhooks - use Stripe CLI + local tunnel or fixture:

```typescript
import { constructEvent } from "@/app/api/webhooks/stripe/route";

it("rejects invalid signature", async () => {
 const req = new Request("http://localhost", {
 method: "POST",
 body: "{}",
 headers: { "stripe-signature": "bad" },
 });
 const res = await POST(req);
 expect(res.status).toBe(400);
});
```

Idempotency: insert same `event.id` twice → second call no-ops.

## Migration gate script

`scripts/check-rls-migration.sh` - run on every migration PR:

```bash
bash scripts/check-rls-migration.sh supabase/migrations/*.sql
```

Fails if new `create table public.*` without `enable row level security`.

## What to test when

| Change | Minimum tests |
|---|---|
| New table | pgTAP RLS matrix + migration gate |
| New storage bucket | pgTAP path isolation |
| New Server Action | Zod unit + auth unauthorized + happy path integration |
| Webhook handler | Signature fail + idempotency + state sync |
| RLS policy change | Update pgTAP - policies regress silently |

## Anti-patterns

| Don't | Do |
|---|---|
| "RLS tested manually once" | pgTAP in CI on every migration |
| Test only happy path | anon + cross-user deny cases |
| E2E only for RLS | pgTAP is faster and precise |
| Skip storage policies | Same rigor as public tables |
| Mock away getUser() always | At least one test proves auth gate |
| Test against prod DB | Local supabase start + reset |

## Composition

| Module | When |
|---|---|
| `enforcement.md` | CI job wiring, maturity L3 |
| `backend-database.md` | Policy patterns to test |
| `backend-storage.md` | Storage RLS tests |
| `backend-webhooks.md` | Webhook integration tests |
| `frontend-testing.md` | Playwright E2E overlap |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
