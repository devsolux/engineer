---
description: Loop until production ship checklist passes - uses /loop dynamic mode.
---

# /engineer-loop-ship

**Loop command** - load engineer `SKILL.md`, `references/workflows.md`, `references/deploy-ops.md`, and the active host’s **`loop`** capability when available.

## Purpose

Iterate on ship gaps until `/engineer-ship` checklist is fully green. **Does not deploy** unless the user explicitly asked to deploy.

## When invoked via /loop

User runs: `/loop dynamic /engineer-loop-ship`

## Each iteration

1. Execute `/engineer-ship` checklist (audit mode - deploy only if user asked)
2. Run verify bundle + RLS gate if migrations exist:
 ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
 npm run typecheck
 bash "$ENGINEER/scripts/engineer-scan.sh" --strict
 bash "$ENGINEER/scripts/check-rls-migration.sh" supabase/migrations/*.sql
 ```
3. If AI tools/MCP changed → `references/ai-security.md` checklist
4. List remaining gaps with severity
5. Fix or recommend `/engineer-enforce` for missing automation
6. Stop when all checklist items ✅ and scans pass

## Stop conditions

- Ship checklist complete
- User says stop
- Blocker needs infra access (secrets, Vercel dashboard) → stop and list manual steps
- Always-ask risk: production deploy requires explicit user yes

## Compose (after green)

| Step | Who |
|---|---|
| Open PR / version / changelog | gstack **`/ship`** |
| Merge + wait CI + deploy | gstack **`/land-and-deploy`** (if configured) |
| Post-deploy health | gstack **`/canary`** |

### Vercel canary notes (when using gstack canary)

- Confirm **production URL** and health path (e.g. `/api/health` or home 200)
- Watch: HTTP 5xx, console errors, CWV regressions if baseline exists
- On red: roll back via Vercel dashboard / previous deployment - do not "fix forward" blindly on money paths
- Always-ask before promoting a bad deploy

## Rules

- Never skip `engineer-scan --strict` when scripts exist
- Never enable paid features without pay on client-only success URLs
- Maker≠checker: checklist evidence required before claiming ship-ready
