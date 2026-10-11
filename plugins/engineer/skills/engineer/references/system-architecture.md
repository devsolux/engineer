# System architecture: patterns, scaling, and decisions

**Last verified**: 2026-07-15 · **Review cadence**: 3 months

How systems are shaped - not folder layout (see `architecture.md` for that).
Full research: `research/coding-research.md`

## Contents
- [Architecture decision process](#architecture-decision-process)
- [Layered model (engineer stack)](#layered-model-engineer-stack)
- [Modular monolith first](#modular-monolith-first)
- [When to split services](#when-to-split-services)
- [Bounded contexts](#bounded-contexts)
- [Data ownership](#data-ownership)
- [Caching architecture](#caching-architecture)
- [Reliability patterns](#reliability-patterns)
- [12-factor essentials](#12-factor-essentials)
- [ADRs](#adrs)
- [Anti-patterns](#anti-patterns)

## Architecture decision process

Before building:

```
1. What is the job of this system? (one paragraph)
2. Who are the actors? (user, admin, webhook, worker)
3. Draw data flow: source → validate → persist → client
4. Choose simplest pattern that meets latency + team size
5. Fill the plan `complexity` receipt; document a decision record if costly or irreversible
```

Use `engineer flow` for cross-service diagrams. See `api-data-flows.md`.

## Layered model (engineer stack)

```
┌─────────────────────────────────────────────────┐
│ Presentation - Next.js RSC + client islands │
│ design tokens · a11y · conversion UX │
├─────────────────────────────────────────────────┤
│ Application - Server Actions · Route Handlers │
│ auth · validation · orchestration │
├─────────────────────────────────────────────────┤
│ Domain - feature modules · business rules │
│ pure functions · Zod schemas · types │
├─────────────────────────────────────────────────┤
│ Data - Supabase Postgres · RLS · Storage │
│ migrations · realtime · edge functions │
├─────────────────────────────────────────────────┤
│ Optional - Rust services (hot path / workers) │
│ Axum · SQLx · queues │
└─────────────────────────────────────────────────┘
```

Dependencies point **inward** - domain never imports UI or HTTP frameworks.

## Modular monolith first

Default for SaaS until proven otherwise:

| Signal | Stay monolith | Consider split |
|---|---|---|
| Team size | <10 engineers | Multiple autonomous teams |
| Traffic | Normal SaaS scale | Measured hot path bottleneck |
| Deploy | Single product | Independent release cycles needed |
| Complexity | CRUD + auth + billing | Heavy streaming / infra proxy |

Structure monolith as **feature modules** with explicit public APIs - future
extraction becomes migration, not rewrite.

## When to split services

Extract Rust/Node/worker service when **measured** need for:
- Sub-50ms p99 on specific endpoint at current load
- WebSocket/stream fanout at scale
- CPU-heavy isolation (PDF, video, ML inference)
- Regulatory/security boundary

Don't split because "microservices are best practice."

Hybrid pattern (common in engineer projects):

```
Next.js (product, auth session, UI)
 ↓ REST/gRPC + JWT
Rust service (hot reads, streaming, workers)
 ↓
Postgres (single source of truth - clear table ownership)
```

## Bounded contexts

Each feature folder ≈ one bounded context:

```
features/
 billing/ # subscriptions, invoices, Stripe
 projects/ # core product entity
 auth/ # signup, session (or lib/supabase)
```

Rules:
- No importing another feature's internals
- Shared kernel in `lib/` only when truly cross-cutting
- Events between contexts: DB triggers, webhooks, or message queue - not direct table writes from foreign feature

## Data ownership

**One writer per table.** Document in ADR or `api-data-flows.md`:

| Table | Owner | Readers |
|---|---|---|
| `projects` | Next Server Actions | RSC, optional Rust read replica |
| `subscriptions` | Stripe webhook handler | App entitlements check |
| `analytics_events` | Client → ingest API | Warehouse |

Anti-pattern: Next and Rust both INSERT into same table without documented owner.

## Caching architecture

Four layers - know which you're debugging (`data-layer.md`):

1. Request memo (`React.cache`)
2. Shared cache (`use cache` + tags)
3. CDN / edge (static assets, public pages)
4. Application cache (Redis in Rust service)

Document freshness SLA per data type. Invalidate explicitly - never "hope it updates."

## Reliability patterns

| Pattern | Use |
|---|---|
| **Timeouts** | Every external I/O (DB, HTTP, Stripe) |
| **Retries with backoff** | Idempotent reads; webhook processing |
| **Circuit breaker** | Calling flaky third parties from Rust |
| **Graceful degradation** | Non-critical features fail soft |
| **Health checks** | `/health/live`, `/health/ready` on services |
| **Idempotency keys** | Payments, webhook handlers |

Design for **failure** - network partitions are normal.

## 12-factor essentials

For deployable apps:

1. **Codebase** - one repo per app (monorepo ok with clear apps/)
2. **Dependencies** - explicit in package.json / Cargo.toml
3. **Config** - env vars; no secrets in code
4. **Backing services** - Supabase/Stripe as attached resources
5. **Build/release/run** - separate stages; CI builds artifact
6. **Processes** - stateless web tier; state in Postgres
7. **Port binding** - self-contained HTTP services
8. **Concurrency** - scale processes, not threads in app code
9. **Disposability** - fast startup, graceful shutdown
10. **Dev/prod parity** - local Supabase mirrors prod schema
11. **Logs** - stdout structured events
12. **Admin processes** - one-off migrations as release step

## ADRs

Architecture Decision Records for non-obvious choices:

```markdown
# ADR-003: Stripe webhooks over client-side subscription check

## Status
Accepted

## Context
Client cannot be trusted for entitlements.

## Decision
Stripe → webhook → Supabase subscriptions table → RLS-scoped app reads.

## Consequences
+ Single source of truth
- Must handle webhook idempotency and retries
```

Store in `docs/adr/` or `architecture/decisions/`.

## Anti-patterns

- Architecture astronautics before first user
- Distributed monolith (microservices sharing one DB with no boundaries)
- Shared mutable state across requests
- Sync call chains >3 hops for user-facing requests
- Cache as afterthought
- No documented data ownership
- Rewriting working stack for resume-driven development

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
