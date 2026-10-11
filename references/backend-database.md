# Backend database: schema, migrations, RLS

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

Postgres via Supabase. **Migrations are source of truth.** RLS is the security
boundary - client-side filters are convenience, not protection.

## Contents
- [Migration workflow](#migration-workflow)
- [Table conventions](#table-conventions)
- [RLS: enable on everything in public](#rls-enable-on-everything-in-public)
- [Policy patterns](#policy-patterns)
- [RLS performance](#rls-performance)
- [Views (Postgres 15+)](#views-postgres-15)
- [Testing RLS](#testing-rls)
- [Storage RLS](#storage-rls)
- [Production checklist](#production-checklist)
- [Anti-patterns](#anti-patterns)

## Migration workflow

```
supabase/migrations/
 20260712120000_create_profiles.sql
 20260712130000_add_projects_rls.sql
```

Naming: `{timestamp}_{verb}_{subject}.sql`

Checklist per migration:
- [ ] RLS enabled on new `public` tables
- [ ] Policies for SELECT/INSERT/UPDATE/DELETE as needed
- [ ] Indexes on FK columns and policy filter columns
- [ ] `updated_at` trigger if rows are edited
- [ ] Types regenerated after apply

```bash
supabase db push # local/dev
supabase gen types typescript --linked > types/database.ts
```

Tables created via raw SQL do **not** auto-enable RLS - always enable explicitly.

## Table conventions

```sql
create table public.projects (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users (id) on delete cascade,
 name text not null,
 status text not null default 'draft'
 check (status in ('draft', 'active', 'archived')),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);

create index projects_user_id_idx on public.projects (user_id);
create index projects_status_idx on public.projects (status);
```

Rules:
- `id uuid primary key default gen_random_uuid()`
- `created_at timestamptz default now()`
- `updated_at` with trigger on editable tables
- `snake_case` in Postgres; map to `camelCase` in TypeScript at boundary
- FK columns always indexed
- Soft deletes only when audit trail required

## RLS: enable on everything in public

```sql
alter table public.projects enable row level security;
```

Default after enable: **deny all** until policies added.

## Policy patterns

### Owner column

```sql
create policy "Users read own projects"
 on public.projects for select
 to authenticated
 using ((select auth.uid()) = user_id);

create policy "Users insert own projects"
 on public.projects for insert
 to authenticated
 with check ((select auth.uid()) = user_id);

create policy "Users update own projects"
 on public.projects for update
 to authenticated
 using ((select auth.uid()) = user_id)
 with check ((select auth.uid()) = user_id);

create policy "Users delete own projects"
 on public.projects for delete
 to authenticated
 using ((select auth.uid()) = user_id);
```

**Always pair `USING` + `WITH CHECK` on UPDATE.** Without `WITH CHECK`, users
can reassign `user_id` to hijack rows.

### Multi-tenant / org

```sql
create policy "Members read org projects"
 on public.projects for select
 to authenticated
 using (
 exists (
 select 1 from public.memberships m
 where m.org_id = projects.org_id
 and m.user_id = (select auth.uid())
 )
 );
```

Prefer membership table over deep joins in every policy. For complex checks,
use `SECURITY DEFINER` helper in private schema.

### Public read, auth write

```sql
create policy "Public read published"
 on public.posts for select
 using (published = true);

create policy "Authors manage own posts"
 on public.posts for all
 to authenticated
 using ((select auth.uid()) = author_id)
 with check ((select auth.uid()) = author_id);
```

## RLS performance

1. **Wrap auth functions**: `(select auth.uid())` not `auth.uid()` - initPlan cache
2. **Index policy columns**: `user_id`, `org_id`, FK used in policies
3. **Specify role**: `to authenticated` / `to anon` - don't rely on defaults
4. **Minimize joins in policies** - use helper functions or denormalized claims
5. **JWT custom claims** for roles when table lookup per row is too slow

```sql
-- Helper for complex membership (security definer, private schema)
create or replace function private.is_org_member(org uuid)
returns boolean language sql stable security definer set search_path = public as $$
 select exists (
 select 1 from memberships
 where org_id = org and user_id = (select auth.uid())
 );
$$;
revoke all on function private.is_org_member(uuid) from public;
grant execute on function private.is_org_member(uuid) to authenticated;
```

## Views (Postgres 15+)

```sql
create view public.active_projects
 with (security_invoker = true) as
 select * from public.projects where status = 'active';
```

Without `security_invoker`, views may bypass underlying RLS.

## Testing RLS

Test matrix (always verify before ship):

| Role | Operation | Expected |
|---|---|---|
| anon | read others' data | deny |
| authenticated | read own data | allow |
| authenticated | read others' data | deny (unless shared) |
| authenticated | update others' row | deny |
| service role | bypass | allow (server jobs only) |

```sql
-- Impersonate in SQL editor / test
set role authenticated;
set request.jwt.claims to '{"sub": "user-uuid-here"}';
select * from public.projects; -- should see only owned rows
reset role;
```

Automate with pgTAP or integration tests against local Supabase.

## Storage RLS

Storage buckets need policies too - see **`backend-storage.md`** for upload
flows, metadata tables, signed URLs, and full policy patterns.

```sql
create policy "Users upload own avatars"
 on storage.objects for insert
 to authenticated
 with check (
 bucket_id = 'avatars'
 and (storage.foldername(name))[1] = (select auth.uid())::text
 );
```

Test with pgTAP - `backend-testing.md` + `templates/supabase/tests/`.

## Production checklist

```
Database ship gate:
- [ ] RLS enabled on all public tables (+ storage buckets)
- [ ] SELECT/INSERT/UPDATE/DELETE policies as needed
- [ ] USING + WITH CHECK paired on UPDATE/INSERT
- [ ] auth.uid() wrapped in (select ...)
- [ ] Policy columns indexed
- [ ] Service role never in client
- [ ] Migrations applied; types regenerated
- [ ] RLS tested with impersonation matrix
- [ ] Views use security_invoker = true
```

## Anti-patterns

- RLS disabled "temporarily"
- INSERT/UPDATE without `WITH CHECK`
- `auth.uid() = user_id` without select wrapper on large tables
- Unindexed `user_id` / `org_id` in policies
- Service role for normal app reads
- Frontend-only authorization (RLS must enforce)
- SECURITY DEFINER functions in exposed `public` schema
- `select("*")` in hot paths (see `data-layer.md`)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
