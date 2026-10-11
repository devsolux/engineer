---
description: Database schema, migrations, and RLS policy plan for Supabase Postgres.
---

# /engineer-schema

Load engineer `SKILL.md`. Routes to **backend-database** + **backend-auth** (not design-system).

User's schema task follows this invocation.

## Output

- Migration SQL plan (`supabase/migrations/{timestamp}_{verb}_{subject}.sql`)
- RLS enable + policies (SELECT/INSERT/UPDATE/DELETE)
- Indexes on FK and policy filter columns
- `(select auth.uid())` wrapper in policies
- RLS test matrix + pgTAP file list
- Type regen command: `supabase gen types typescript --linked`

## Hard gates

- RLS on every new `public` table
- USING + WITH CHECK paired on UPDATE
- Run `check-rls-migration.sh` on new migration files

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
bash "$ENGINEER/scripts/check-rls-migration.sh" supabase/migrations/*.sql
supabase test db  # when local supabase running
```

## After schema approved

Implement with `/engineer` or `/engineer-api` for Server Actions.
