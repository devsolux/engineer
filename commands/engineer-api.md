---
description: Server Actions, Route Handlers, and API mutations with auth, Zod, and RLS.
---

# /engineer-api

Load engineer `SKILL.md`. Pipeline: **backend-api → backend-auth → backend-database → data-layer**.

API task follows this invocation.

## Mutation pipeline (always)

```
Rate limit (if sensitive)
  → Zod validate
  → getUser()
  → Authorize (RLS + explicit)
  → Mutate
  → updateTag / revalidateTag
```

## Hard gates

- `getUser()` not `getSession()` alone on mutations
- Zod on every external input
- No service role in client bundles
- Webhooks: `backend-webhooks.md` + gstack `/cso`

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
npm run typecheck
bash "$ENGINEER/scripts/engineer-scan.sh" --backend --strict
```

## Related

- Data flow diagram first: `/engineer-flow`
- Stripe: `/engineer-billing`
