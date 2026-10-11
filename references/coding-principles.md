# Coding principles: standards, craft, and pragmatism

**Last verified**: 2026-07-15 · **Review cadence**: 3 months

How to write code that survives teams, AI assistants, and year-two refactors.
Full research: `research/coding-research.md`

## Contents
- [Core philosophy](#core-philosophy)
- [Principles (when to apply)](#principles-when-to-apply)
- [SOLID at the right granularity](#solid-at-the-right-granularity)
- [Proportionality gate](#proportionality-gate)
- [Naming and intent](#naming-and-intent)
- [Functions and modules](#functions-and-modules)
- [Abstraction rules](#abstraction-rules)
- [Error handling philosophy](#error-handling-philosophy)
- [Testing philosophy](#testing-philosophy)
- [Observability](#observability)
- [Code review standards](#code-review-standards)
- [Anti-patterns](#anti-patterns)

## Core philosophy

1. **Optimize for change** - code is read and modified 10× more than written
2. **Explicit over clever** - boring code beats smart code in production
3. **Measure maintainability** - cycle time, defect rate, deploy frequency - not line count
4. **Minimal diff** - smallest change that solves the problem; match repo conventions
5. **Enforce what matters** - see `enforcement.md`; principles without gates decay

Clean Code heuristics are useful; **modern software engineering** adds feedback loops
(CI, tests, observability) that force complexity visible. Both apply.

## Principles (when to apply)

| Principle | Meaning | Apply when |
|---|---|---|
| **KISS** | Simplest solution that works | Always default |
| **YAGNI** | Don't build for hypothetical futures | Greenfield features |
| **DRY** | Single source of truth | Third duplicate appears (Rule of Three) |
| **SRP** | One reason to change per module | Class/service grows mixed concerns |
| **Fail fast** | Reject invalid state early | Boundaries, parsers, auth |
| **Defense in depth** | Multiple independent checks | Security, auth, payments |
| **Boy Scout** | Leave code slightly better | Touching a file anyway |

**Rule of Three**: tolerate duplication twice; abstract on the third occurrence.
Premature abstraction is harder to undo than duplication.

## SOLID at the right granularity

In 2026 fullstack apps, map SOLID to **boundaries**, not tiny classes:

| Principle | Class-level | Service / feature-level |
|---|---|---|
| **S** Single Responsibility | One job per module | One bounded context per feature folder |
| **O** Open/Closed | Strategy over switch | Extend via new handlers/events, not editing core |
| **L** Liskov Substitution | Subtypes honor contracts | API versions don't break clients silently |
| **I** Interface Segregation | Small interfaces | Narrow API surface; no god REST routes |
| **D** Dependency Inversion | Depend on abstractions | Domain logic doesn't import infra directly |

Ask **"At what granularity?"** before citing SOLID in review.

SOLID is diagnostic, not a quota. A principle justifies structure only when an observed
change pressure, substitutability contract, client split, or infrastructure boundary exists.
Never add an interface, base class, adapter, service, or event bus merely to make a diagram
look SOLID. State the concrete pressure and boundary; otherwise keep the direct dependency.

Skip heavy SOLID in:
- One-off scripts
- Throwaway prototypes
- <50 lines that won't change

Apply when change friction appears: every new variant edits the same file.

## Proportionality gate

For every approved multi-file plan, complete the `complexity` receipt in
`templates/plan.sample.json` and validate it with `scripts/validate-plan.sh`.

| Question | Default | Evidence that can override it |
|---|---|---|
| Add abstraction? | No; inline or tolerate two duplicates | Third real use, implementation swap, or repeated shotgun change |
| Add runtime component? | No; use the existing process/database | Measured SLO, isolation, ownership, compliance, or durability need |
| Split service/package? | Modular monolith | Independent deploy/team/data boundary or measured hot path |
| Build generic framework? | Solve the present concrete case | Multiple current consumers with a stable shared contract |
| Optimize performance? | Readable implementation | Profile/trace/benchmark identifies the bottleneck |
| Add configurability? | One explicit default | Current tenant/product variants—not imagined futures |

Classify decisions as reversible, costly, or irreversible. Prefer small reversible changes;
costly or irreversible choices require a decision record and rollback/migration path. Security,
privacy, accessibility, data integrity, and payment controls are essential complexity, not
overengineering; simplify their implementation but never delete the boundary.

Review the total system, not only line count. Extra services, queues, caches, flags, layers,
schemas, generated files, dependencies, CI jobs, prompts, and agent roles all spend complexity
budget. A shorter function can still create a more complicated system.

## Naming and intent

- **Domain language** - `SettlementBatchProcessor` not `DataHandler`
- **Auxiliary verbs** - `isLoading`, `hasError`, `canSubmit`
- **Verbs for functions** - `createProject`, `validateCheckout`, `mapToDto`
- **No abbreviations** unless universal (`id`, `url`, `dto`)
- **Booleans** - `is*`, `has*`, `should*`; never `flag`
- **Files match export** - `pricing-table.tsx` exports `PricingTable`

Generic names (`data`, `handler`, `utils`) confuse humans **and AI tools**.

## Functions and modules

- **One level of abstraction per function** - don't mix SQL, business rules, and HTTP mapping
- **Early returns** - guard clauses at top; avoid deep nesting (>3 levels)
- **Pure when possible** - side effects at edges (handlers, actions)
- **File size guide** - split around **150-250 lines** when responsibilities diverge
- **Colocate** - schema, action, component for one feature live together

Don't split a 80-line cohesive function into 8 files for "clean code."

## Abstraction rules

```
Need abstraction?
 └─ Seen this pattern 3+ times? → extract
 └─ Swapping implementation (payment, storage)? → interface
 └─ Cross-cutting (logging, auth)? → middleware/wrapper
 └─ Otherwise → inline
```

Forbidden until proven:
- Repository pattern over Supabase client (unless testing requires it)
- Generic `BaseService` / `AbstractController`
- Factory-of-factory patterns
- Microservices before team/monolith pain

Prefer **modular monolith** → extract service when scaling or team boundary demands it.
See `system-architecture.md`.

## Error handling philosophy

| Layer | Pattern |
|---|---|
| Domain | Typed errors / Result types |
| Server Action | `{ ok, data \| error }` - user-safe messages |
| Route Handler | HTTP status + JSON `{ error, code? }` |
| Rust | `AppError` → `IntoResponse` |
| Client | Error boundary + retry where appropriate |

Rules:
- **Never swallow errors** - log with context (userId, requestId, action)
- **Never leak internals** to users (stack traces, SQL errors)
- **Validate at boundary** - Zod on every external input
- **Idempotency** on payments and webhooks

## Testing philosophy

Pyramid (see `frontend-testing.md` for UI):

```
Many fast unit tests (pure logic, schemas)
 → fewer integration tests (DB, auth, actions)
 → few E2E tests (critical user journeys)
```

- Test **behavior**, not implementation
- Test **regression-prone** paths: auth, RLS, billing, permissions
- Don't test framework behavior or trivial getters
- Prefer real DB (Testcontainers / local Supabase) over heavy mocking for data layer

## Observability

Maintainable systems are **traceable**:

- Structured logs (JSON) with `traceId`, `userId`, `action`
- OpenTelemetry traces on request path (Next → Supabase → Rust)
- Metrics: latency p95, error rate, saturation
- **60-second rule**: can a dev follow one request end-to-end?

Emit events on state changes, not string spam.

## Code review standards

Reviewer checklist:

- [ ] Solves the stated problem - no scope creep
- [ ] Auth + validation on mutations
- [ ] Types accurate; no silent `any`
- [ ] Errors handled; user-safe messages
- [ ] Loading/empty/error states (UI)
- [ ] Tests for non-trivial logic
- [ ] Naming matches domain
- [ ] Diff minimal; follows repo patterns
- [ ] No secrets; no hardcoded colors
- [ ] Migration + RLS if schema changed

Feedback format: **quote → rule → fix** (same as `engineer audit`).

## Anti-patterns

- Clever one-liners over readable logic
- Abstraction before duplication proves itself
- 5-line function religion causing shotgun surgery
- Comments explaining *what* instead of *why*
- God files (`utils.ts`, `helpers.ts`, `misc.ts`)
- Optimistic refactor bundled with feature PR
- Copy-paste from Stack Overflow without domain fit
- Ignoring linter because "will fix later"
- Tests that mock everything and assert nothing

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
