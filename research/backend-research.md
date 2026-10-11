# Backend research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `backend-auth.md`, `backend-database.md`, `backend-api.md`, `backend-webhooks.md`, `data-layer.md`, `rust.md`, `api-data-flows.md`

## Executive summary

2026 fullstack backend standards (Next.js + Supabase + optional Rust):

1. **RLS is the security boundary** — enable on all `public` tables; deny-by-default
2. **Cookie SSR auth** — middleware with `getAll`/`setAll`; `getUser()` on server mutations
3. **Server Actions are public POST endpoints** — auth + Zod + rate limit on every action
4. **Defense in depth** — middleware + app auth + RLS + validation (never one layer alone)
5. **Migrations as source of truth** — SQL in repo; regenerate TS types after apply
6. **Cache split (Next 16)** — `updateTag` in Server Actions; `revalidateTag` in Route Handlers
7. **Webhooks** — verify signature on raw body; idempotency on event ID; 200 fast
8. **Rust for hot paths** — Axum + SQLx; one owner per table; contract-first TS boundary

---

## 1. Supabase SSR auth

**Sources**: supabase.com/docs, @supabase/ssr, @supabase/server, SecureStartKit 2026

### Architecture

```
Browser → Middleware (refresh session, setAll cookies)
       → RSC/Action (createServerClient, getUser())
       → Supabase PostgREST (anon key + JWT → RLS)
```

### Critical rules

- **New client per request** — never share across requests
- **Middleware mandatory** for SSR cookie auth
- **`setAll` required** — token refresh writes cookies back to response
- **Cache headers on auth responses** — don't cache at CDN (session bleed risk)
- **`getClaims()`** in middleware for route gating (local JWT verify)
- **`getUser()`** in Server Components/Actions (server-validated)
- **Never `getSession()` alone** for auth decisions on server
- **Never service role in client** — bypasses all RLS

### @supabase/server (2026)

Composable with `@supabase/ssr`:
- SSR package = cookie lifecycle
- Server package = JWT verify, context client, admin helpers

Default engineer: `@supabase/ssr`. Advanced multi-runtime: add `@supabase/server`.

---

## 2. Row Level Security (Postgres)

**Sources**: supabase.com/docs RLS, MakerKit RLS guide, llmbestpractices.com, Supabase troubleshooting (RLS performance)

### Mental model

RLS adds implicit WHERE to every query. With anon key exposed to browser,
**RLS is the only line that matters**. Frontend checks are UX, not security.

### Enable everywhere

Tables from SQL editor ship with RLS **OFF**. Always:

```sql
alter table public.my_table enable row level security;
```

Default: deny all until policies added.

### Policy anatomy

| Clause | Purpose |
|---|---|
| `USING` | Which existing rows visible (SELECT/UPDATE/DELETE) |
| `WITH CHECK` | What new values allowed (INSERT/UPDATE) |
| `TO role` | Scope to `authenticated`, `anon`, etc. |

**UPDATE needs both USING and WITH CHECK** — prevents `user_id` hijack.

### Six common patterns

1. User-scoped (`auth.uid() = user_id`)
2. Multi-tenant org (membership table + exists)
3. Shared resources (membership + role)
4. Role-based (JWT claim or role table)
5. Public read / auth write
6. Soft-delete visibility (`deleted_at is null`)

### Performance (100x gains possible)

1. Wrap: `(select auth.uid()) = user_id` not bare `auth.uid()`
2. Index every column used in policies
3. Specify `TO authenticated` explicitly
4. Minimize joins in policies — use SECURITY DEFINER helpers in private schema
5. JWT custom claims for roles when table lookup per row is slow

### SECURITY DEFINER functions

Use for complex membership checks. Rules:
- Place in **private schema**, not `public`
- `set search_path = public`
- Verify caller inside function
- `REVOKE EXECUTE FROM PUBLIC`; grant to `authenticated` only

### Views

Postgres 15+: `security_invoker = true` or views bypass underlying RLS.

### Testing

Impersonate roles in SQL editor or automate with pgTAP. Matrix:
anon / authenticated own / authenticated other / service role.

---

## 3. Server Actions security (2026)

**Sources**: nextjs.org Server Actions docs, MakerKit secure actions, DigitalApplied 2026 patterns, DevRadar, Adamarant security advisories

### Framework provides

- POST-only invocation
- Origin vs Host CSRF comparison
- Encrypted action IDs (non-enumerable)
- Closed-over variable encryption per build

### You must provide

1. Input validation (Zod)
2. Authentication (`getUser()`)
3. Authorization (ownership/role)
4. Rate limiting (sensitive actions)
5. Safe return values (no secrets in response)

### Server Actions = public HTTP endpoints

Any client that discovers the action ID can POST. CSRF blocks cross-origin
form posts but **not unauthenticated same-origin abuse**.

### Rate limiting

Order: auth → rate limit → validate → mutate (authenticated)
Or: rate limit → validate → mutate (anonymous)

Use Upstash Redis or equivalent. Key by user ID or IP.

### Production config

```typescript
experimental: {
  serverActions: {
    bodySizeLimit: "2mb",
    allowedOrigins: ["https://yourdomain.com"],
  },
}
```

Set `allowedOrigins` for reverse proxies and preview deploys.

### Data Access Layer (DAL)

Centralize `getUser()` + queries in `server-only` modules. Prevents scattered
auth checks and duplicate fetch logic.

### Security maintenance

Keep Next.js patched — 2026 advisories covered middleware bypass, SSRF, XSS,
cache poisoning. Audit `allowedOrigins` on deploy.

---

## 4. Route Handlers vs Server Actions

**Sources**: nextjs.org Route Handlers, caching docs

| Use Server Action | Use Route Handler |
|---|---|
| Browser form mutations | Webhooks (Stripe, etc.) |
| Progressive enhancement | Mobile/external REST clients |
| `updateTag` immediate cache | `revalidateTag` invalidation |
| Same-origin app | Signature verification on raw body |

### HTTP semantics

Return correct status codes. Never 200 on validation failure for APIs.

### Cache invalidation split (Next 16)

- **`updateTag(tag)`** — Server Actions only; immediate expiry (read-your-own-writes)
- **`revalidateTag(tag, profile)`** — Route Handlers, webhooks; stale-while-revalidate

Calling `updateTag` outside Server Action throws at runtime.

---

## 5. Database schema and migrations

**Sources**: supabase.com migrations, Supabase vibe-coders environments guide

### Conventions

- Timestamp-prefixed migration files
- UUID PKs with `gen_random_uuid()`
- `timestamptz` for all timestamps
- `snake_case` in DB; camelCase at TS boundary
- FK columns indexed
- `updated_at` trigger on editable tables

### Type generation

```bash
supabase gen types typescript --linked > types/database.ts
```

Run after every migration apply.

### Multi-environment

Local → staging → prod with same migration files. Never hand-edit prod schema.

---

## 6. Caching and data layer

**Sources**: nextjs.org v16 caching, use cache, cacheLife, cacheTag

### Four layers

1. Request memoization — `React.cache()`
2. Data cache — `use cache` + `cacheLife`
3. Full route cache — static shell
4. Client router cache — navigation stale time

### use cache rules

- On data functions or leaf components — not page orchestrators
- Explicit `cacheLife` always
- User-specific: auth outside cache scope, pass userId as arg
- Never `cookies()`/`headers()` inside `use cache`

### Invalidation registry

Maintain cache tag registry as app grows. Document which tags each entity uses.

### Supabase query rules

- Select only needed columns
- Push filters to DB
- Paginate unbounded lists
- `Promise.all` for independent reads

---

## 7. Webhooks and payments

**Sources**: Stripe docs, SecureStartKit, MakerKit

### Stripe inbound

1. Read **raw body** (`req.text()`)
2. `stripe.webhooks.constructEvent(body, sig, secret)`
3. Idempotency on `event.id` in DB or Redis
4. Process; return 200
5. Return 500 on failure (Stripe retries)

### Idempotency

- Webhooks: dedupe on event ID
- Stripe API calls: `idempotencyKey` header
- Redis `SET NX` for short-lived locks

### Subscription sync

Stripe = billing source of truth. Webhooks sync entitlements to Supabase.
Never trust client-side subscription state.

---

## 8. Edge Functions and workers

**Sources**: supabase.com Edge Functions docs

Use for:
- Scheduled/cron jobs
- Webhook receivers near DB
- Isolation from Next runtime

Rules:
- Verify caller (JWT, shared secret)
- Service role server-side only
- Don't expose open endpoints

---

## 9. Rust services (hybrid stack)

**Sources**: Axum docs, Tower, SQLx; engineer rust.md

When TS/Supabase isn't enough:
- High throughput, streaming, workers, proxies

Rules:
- One owner per table (TS or Rust, not both writing blindly)
- OpenAPI/proto contract-first
- Session stays in Next; Rust gets JWT/service token
- No unwrap in handlers; I/O timeouts; graceful shutdown

---

## 10. Module map → engineer references

| Research area | Reference module |
|---|---|
| Auth SSR, sessions | `backend-auth.md` |
| Schema, RLS, migrations | `backend-database.md` |
| Server Actions, Route Handlers | `backend-api.md` |
| Webhooks, Stripe, Edge Functions | `backend-webhooks.md` |
| Queries, cache, realtime | `data-layer.md` |
| Cross-service flows | `api-data-flows.md` |
| Rust/Axum | `rust.md` |
| TS validation, Result types | `typescript.md` |

---

## Canonical sources

### Supabase
- https://supabase.com/docs/guides/auth/server-side/creating-a-client
- https://supabase.com/docs/guides/database/postgres/row-level-security
- https://github.com/supabase/ssr

### Next.js
- https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations
- https://nextjs.org/docs/app/api-reference/functions/updateTag
- https://nextjs.org/docs/app/api-reference/functions/revalidateTag
- https://nextjs.org/docs/app/building-your-application/routing/route-handlers

### Security
- https://makerkit.dev/blog/tutorials/secure-nextjs-server-actions
- https://makerkit.dev/blog/tutorials/supabase-rls-best-practices
- https://llmbestpractices.com/backend/supabase-rls

### Payments
- https://docs.stripe.com/webhooks
- https://docs.stripe.com/api/idempotent_requests

### Rust
- https://docs.rs/axum/latest/axum/
- https://github.com/launchbadge/sqlx

### Cross-ref
- `research/report.md` (stack notes)
- `research/frontend-research.md` (RSC/data fetching client boundary)
