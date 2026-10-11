# Backend: Supabase, auth, API - router

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

Router for backend implementation. Deep dives in sibling modules:

| Topic | Module |
|---|---|
| SSR auth, middleware, sessions | `backend-auth.md` |
| Migrations, schema, RLS, indexes | `backend-database.md` |
| File uploads, Storage buckets | `backend-storage.md` |
| pgTAP, RLS integration tests | `backend-testing.md` |
| Server Actions, Route Handlers, DAL | `backend-api.md` |
| Stripe webhooks, idempotency | `backend-webhooks.md` | cso |
| Checkout, Portal, billing | `billing-stripe.md` | cso |
| App security, CSP | `backend-security.md` | cso |
| Queries, cache, realtime | `data-layer.md` |
| Cross-service flows | `api-data-flows.md` |
| Rust services | `rust.md` |
| TS types, Zod, Result types | `typescript.md` |

Full research corpus: `research/backend-research.md`

## Quick reference

### Stack layout

```
lib/supabase/ # client, server, middleware
lib/dal/ # server-only data access (optional)
features/*/actions.ts # Server Actions colocated
features/*/schema.ts # Zod shared client + server
app/api/webhooks/ # Route Handlers for external
supabase/migrations/ # SQL source of truth
```

### Mutation pipeline (always)

```
Rate limit (if sensitive)
 → Zod validate
 → getUser() / verify token
 → Authorize (RLS + explicit)
 → Mutate
 → updateTag (Action) or revalidateTag (Handler)
```

### Security layers (defense in depth)

| Layer | Enforces |
|---|---|
| Middleware | Session refresh; optional route gate |
| Server Action/Handler | Auth + validation + rate limit |
| Supabase RLS | Row access in Postgres |
| Zod | Input shape at TS boundary |

### Hard gates

- RLS on every `public` table (+ storage buckets)
- `getUser()` on server mutations - not `getSession()` alone
- Middleware `getAll` + `setAll` on cookies
- Zod on every external input
- Service role server-only
- Webhook signature verify before parse
- Idempotency on payment/subscription events

See submodule anti-patterns for detailed lists.

## When to use what

| Need | Path |
|---|---|
| Form submit in app | Server Action |
| Stripe webhook | Route Handler → `backend-webhooks.md` |
| New subscription / checkout | `billing-stripe.md` |
| OAuth callback | Route Handler |
| Dashboard data | RSC + DAL → `data-layer.md` |
| Avatar / file upload | `backend-storage.md` → `backend-api.md` |
| Multi-tenant schema | `backend-database.md` RLS patterns |
| High-throughput API | `rust.md` + `api-data-flows.md` |
| Scheduled job | Edge Function or external worker |

## Composition

| Skill | When |
|---|---|
| gstack `cso` | Before payment/auth webhooks ship |
| gstack `qa` | E2E on auth + critical mutations |
| `engineer schema` | Migration + RLS planning verb |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
