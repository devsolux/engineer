# Coding & architecture research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `coding-principles.md`, `system-architecture.md`, `architecture.md`, `code-quality.md`

## Executive summary

2026 software craft balances **Clean Code heuristics** with **engineering feedback loops**:

1. **Optimize for change** — maintainability = low cognitive load + fast feedback
2. **SOLID at boundaries** — feature modules and services, not 5-line functions
3. **Rule of Three** — duplicate twice; abstract on third occurrence
4. **Modular monolith first** — split services on measured need, not fashion
5. **One writer per table** — clear data ownership across TS/Rust/Supabase
6. **Observability from day one** — traceable requests or unmaintainable system
7. **Explicit domain naming** — anchors human + AI understanding
8. **Enforce via CI** — principles without gates decay (see `enforcement-research.md`)

---

## 1. Clean Code vs modern software engineering

**Sources**: Robert C. Martin (Clean Code), Modern Software Engineering (David Farley), Uğur Kaval 2026 maintainability guide

### Clean Code — still valid

- Meaningful names
- Small functions *when cohesion allows*
- Single level of abstraction
- Error handling not mixed with happy path
- Tests as documentation of behavior

### Where Clean Code is insufficient

- Doesn't address **deployment frequency**, **observability**, **system boundaries**
- "5-line functions" → shotgun surgery across 15 files
- Local readability ≠ system changeability

### Modern engineering adds

- Short feedback loops (CI minutes, not days)
- Trunk-based development
- Feature flags
- Metrics: cycle time, MTTR, change fail rate
- Complexity forced visible by frequent integration

**engineer stance**: Use Clean Code as heuristics; enforce with tests, CI, traces.

---

## 2. SOLID in 2026

**Sources**: Banandre SOLID 2026, BackendBytes production guide, Md Sanwar Hossain complete guide

### Granularity shift

| Era | SOLID applied to |
|---|---|
| 2000s | Classes and inheritance |
| 2026 | Services, API contracts, event schemas, feature folders |

### Per-principle (when to apply)

**SRP** — Extract when module changes for unrelated reasons (billing + auth in one file).
At service level: one bounded context per deployable or feature folder.

**OCP** — Replace growing switch statements with strategy/plugin registration.
At API level: new behavior via new endpoints/events, not editing core handler.

**LSP** — Subtypes must honor behavioral contracts (latency, errors, side effects).
At API level: v2 doesn't break v1 clients; error shapes consistent.

**ISP** — Split fat interfaces by consumer need.
At API level: narrow REST surface; separate read/write admin APIs.

**DIP** — High-level policy doesn't import low-level infra.
Domain defines interface; Supabase/Stripe implement at edge.
Enables testing without DB.

### When to skip SOLID

- Scripts, prototypes, one-off migrations
- Code with zero expected change
- When abstraction cost > duplication cost

---

## 3. Other principles

| Principle | 2026 interpretation |
|---|---|
| **DRY** | Single source of truth — but duplicate until pattern clear |
| **KISS** | Default; complexity needs justification |
| **YAGNI** | No speculative frameworks |
| **LoD** (Law of Demeter) | Don't chain `a.b.c.d` — tell, don't ask |
| **Composition > inheritance** | Especially React and TS |
| **Fail fast** | Validate at boundary; reject early |
| **Boy Scout rule** | Small improvements in touched files |

---

## 4. Cognitive load and AI-era maintainability

**Sources**: Uğur Kaval 2026, industry LLM copilot usage studies

- **70%+ boilerplate** may be AI-generated — humans architect and debug
- **Clever code** breaks AI assistance and on-call debugging
- **Domain-specific names** anchor LLM context (`InvoiceReconciliation` not `Processor`)
- **Comments** explain *why*; code explains *what*
- **Traces > comments** for production truth

File size heuristic: split at **150–250 lines** when responsibilities diverge — not at arbitrary 20 lines.

---

## 5. System architecture patterns

**Sources**: Martin Fowler, 12-factor app, ProductQuant PLG architecture, engineer api-data-flows

### Default stack shape

```
Next.js modular monolith
  → Supabase Postgres (RLS)
  → optional Rust for hot path
  → Stripe for billing
  → analytics warehouse (later)
```

### Modular monolith benefits

- Single deploy, shared types, simpler debugging
- Feature folders prepare future extraction
- Scales to millions of users with Postgres + caching before split

### Microservices triggers (all should be measured)

- Independent scaling of CPU-bound workload
- Team autonomy (Conway's law)
- Different availability/security requirements
- Regulatory isolation

### Anti-patterns

- Distributed monolith (many services, one DB, tangled calls)
- Premature microservices (<10 engineers)
- Shared tables with multiple writers

---

## 6. Data ownership & bounded contexts

Each bounded context owns:
- Its tables (write authority)
- Its Server Actions / handlers
- Its events

Cross-context communication:
- Public API on feature `index.ts`
- Domain events (webhook, queue, DB NOTIFY)
- Never reach into `features/other/internal/`

---

## 7. Reliability & operability

**Sources**: Google SRE, Axum production patterns, Next.js 2026 security advisories

Essentials:
- Timeouts on all I/O
- Structured JSON logging + trace IDs
- Health endpoints
- Graceful shutdown
- Idempotent webhooks
- Rate limits on public mutations

**60-second debug rule**: new engineer traces request path in one minute.

OpenTelemetry: traces + logs + metrics correlated.

---

## 8. Testing philosophy

**Sources**: Kent C. Dodds testing trophy, engineer frontend-testing.md

- Many unit tests for pure logic
- Integration tests for auth, RLS, actions
- Few E2E for critical journeys
- Test behavior not implementation
- Prefer real DB over mock soup for data layer

---

## 9. Code review & ADRs

**Review focuses on**: correctness, security, maintainability, scope — not bike-shedding style.

**ADRs** for irreversible decisions: database choice, auth model, monolith vs split, event bus.

Template: Context → Decision → Consequences.

---

## 10. Module map

| Topic | Reference |
|---|---|
| Daily coding rules | `coding-principles.md` |
| System patterns | `system-architecture.md` |
| Folder layout | `architecture.md` |
| Ship gates | `code-quality.md` |
| CI enforcement | `enforcement.md` |
| Data flows | `api-data-flows.md` |

---

## Canonical sources

- Robert C. Martin — Clean Code, Clean Architecture
- David Farley — Modern Software Engineering
- https://12factor.net/
- https://backendbytes.com/articles/solid-principles-clean-code/
- https://www.ugurkaval.com/blog/maintainable-code-engineering-practices-2026
- https://martinfowler.com/architecture/
