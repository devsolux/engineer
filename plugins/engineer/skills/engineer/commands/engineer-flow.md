---
description: Sketch cross-service data flows before coding — TS, Rust, Supabase, webhooks.
---

# /engineer-flow

Load engineer `SKILL.md`. Routes: **api-data-flows → system-architecture**.

Feature or integration follows this invocation.

## Output (required)

```markdown
## Flow diagram (mermaid or ASCII)
## Sources of truth
## Auth boundaries
## Validation points (Zod)
## Persistence (RLS tables)
## Client read path (RSC / Query)
## Error + timeout strategy
## Caching / revalidation tags
```

## Rules

- **No implementation code** until user approves flow (unless they said "and build")
- Hybrid TS + Rust → also load `rust.md`
- Webhooks → mark idempotency + signature verify step

## After approval

`/engineer-api` or `/engineer` to implement.
