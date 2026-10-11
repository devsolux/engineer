# APIs and data flows

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `backend-api.md` | Next.js Actions, handlers |
| `backend-webhooks.md` | Inbound events |
| `rust.md` | Rust service boundary |
| `system-architecture.md` | Monolith vs services |

Cross-cutting module for how data moves through TypeScript, Rust, Supabase,
and the client. **Always sketch the flow before implementing.**

## Contents
- [Flow template](#flow-template)
- [Architecture patterns](#architecture-patterns)
- [Next.js data paths](#nextjs-data-paths)
- [Rust service paths](#rust-service-paths)
- [Hybrid TS + Rust](#hybrid-ts--rust)
- [Webhooks and events](#webhooks-and-events)
- [Caching in the flow](#caching-in-the-flow)
- [Auth in the flow](#auth-in-the-flow)
- [Anti-patterns](#anti-patterns)

## Flow template

Before coding, document:

```
Source → Validate → Authz → Transform → Persist → Cache → Response → Client

Example (create project):
 Browser form
 → Server Action (Zod)
 → getUser()
 → INSERT projects (RLS)
 → revalidateTag("projects")
 → Result<ProjectDto>
 → optimistic UI update
```

Include: failure points, retry behavior, idempotency, observability hooks.

## Architecture patterns

| Pattern | Shape | Best for |
|---|---|---|
| **Server Action direct** | Client → RSC/Action → Supabase | App mutations, simple CRUD |
| **Route Handler API** | Client/external → `/api/*` → DB/service | Webhooks, mobile, third-party |
| **BFF** | Client → Next API → Rust/Supabase | Hide internal services, aggregate |
| **Rust service** | Client/gateway → Axum → Postgres/Redis | Hot path, streaming, infra |
| **Event-driven** | Producer → queue → worker → DB | Async, decoupled, high volume |
| **Read-through cache** | Client → cache → miss → DB → fill | Read-heavy public data |

Choose the **simplest pattern that meets latency and ownership needs**.

## Next.js data paths

### Read (RSC)

```
page.tsx → query fn (server) → Supabase/Rust/fetch
 → React.cache / use cache (if shared + staleable)
 → pass serializable props → Client island (if needed)
```

### Write (Server Action)

```
form → Server Action → Zod → auth → mutate → revalidate → Result
```

### External API (Route Handler)

```
POST /api/webhooks/stripe → verify signature → Zod → idempotent handler → 200
```

Rules:
- Parallelize independent reads (`Promise.all`)
- Never sequential-await independent sources
- User-specific data: auth outside `use cache`, pass as argument

## Rust service paths

### Sync REST

```
Client → Axum handler → validate → domain → SQLx → JSON response
 ↑ TraceLayer logs request_id + latency
```

### Streaming (gRPC / WebSocket)

```
Client → connect → auth on upgrade → stream handler
 → backpressure aware → graceful disconnect
```

## Hybrid TS + Rust

Typical split for fullstack products:

```
┌─────────────────────────────────────────┐
│ Next.js (TypeScript) │
│ UI · Server Actions · Auth session │
│ Supabase RLS for app data │
└──────────────┬──────────────────────────┘
 │ REST/gRPC (contract-first)
┌──────────────▼──────────────────────────┐
│ Rust service (Axum) │
│ Hot path · streaming · proxy · workers │
└──────────────┬──────────────────────────┘
 │
 Postgres / Redis / external APIs
```

Rules:
- **Session stays in Next** - Rust receives JWT or service token, not cookies directly (unless gateway)
- **OpenAPI or proto** defines the contract
- **Errors**: consistent JSON shape both sides `{ error, code? }`
- **Timeouts**: TS fetch to Rust must have explicit timeout + retry policy

## Webhooks and events

Inbound webhook flow:

1. Verify signature (Stripe, Supabase, etc.)
2. Parse + Zod validate payload
3. Idempotency check (event ID in DB)
4. Process or enqueue
5. Return 200 quickly (process async if heavy)

Outbound events:

1. Mutate in transaction
2. Emit event (queue/notify)
3. Worker processes with retry + dead letter

## Caching in the flow

| Layer | Tool | Invalidation |
|---|---|---|
| Per-request | `React.cache()` | automatic (request scope) |
| Shared read | `use cache` + `cacheLife` | `updateTag` / `revalidateTag` |
| HTTP | `Cache-Control` on Route Handler | explicit |
| Rust | moka/redis in service | TTL + event invalidation |
| Client | TanStack Query (if present) | query key + staleTime |

Document which layer owns freshness for each data type.

## Auth in the flow

| Layer | Check |
|---|---|
| Middleware | Session refresh; `getClaims()` for route gate |
| Server Action / RSC | `getUser()` |
| Route Handler | Bearer/API key/JWT + scope |
| Supabase RLS | `auth.uid()` on every row |
| Rust service | JWT/API key extractor; never trust client claims without verify |

Auth decision and data access must **align** - don't auth in TS then bypass in Rust.

## Anti-patterns

- Mystery meat data flow (can't draw the diagram)
- Client fetching secrets or service endpoints
- Double writes (TS and Rust both mutate same table)
- No idempotency on webhooks
- Caching user-specific data without user in cache key
- Rust service with no timeouts
- God `/api` route that does everything
- Skipping validation because "it's internal"

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
