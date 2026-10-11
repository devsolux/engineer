-- pgTAP template: RLS isolation for public.projects
-- Copy to: supabase/tests/rls_projects.test.sql
-- Run: supabase start && supabase db reset && supabase test db
--
-- Requires: projects table with user_id + RLS enabled (see backend-database.md)

begin;
select plan(5);

-- ---------------------------------------------------------------------------
-- 1. Anonymous access denied
-- ---------------------------------------------------------------------------
set local role anon;

select is(
  (select count(*)::int from public.projects),
  0,
  'anon cannot read projects'
);

select throws_ok(
  $$ insert into public.projects (user_id, name)
     values ('00000000-0000-0000-0000-000000000001', 'anon hack') $$,
  'new row violates row-level security policy',
  'anon cannot insert projects'
);

-- ---------------------------------------------------------------------------
-- 2. Authenticated isolation (extend with your test user JWT helpers)
-- Use supabase test helpers or seed auth.users in supabase/seed.sql
-- ---------------------------------------------------------------------------
-- set local role authenticated;
-- select set_config('request.jwt.claim.sub', '<user-a-uuid>', true);
-- select lives_ok($$ insert into public.projects (user_id, name)
--   values ('<user-a-uuid>', 'mine') $$, 'owner can insert');
-- select set_config('request.jwt.claim.sub', '<user-b-uuid>', true);
-- select is((select count(*) from public.projects where user_id = '<user-a-uuid>'), 0::bigint,
--   'user B cannot read user A projects');

select pass('extend authenticated isolation tests with seeded users');

select finish();
rollback;
