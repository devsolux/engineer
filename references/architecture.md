# Architecture: structure, scaling, conventions

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

Folder layout and repo conventions. For **system design patterns** (monolith vs
services, bounded contexts, reliability) see `system-architecture.md`. For **coding
standards** see `coding-principles.md`.

## Contents
- [Recommended layout](#recommended-layout)
- [Naming conventions](#naming-conventions)
- [Feature boundaries](#feature-boundaries)
- [Scaling patterns](#scaling-patterns)
- [Monorepo (Turbo)](#monorepo-turbo)
- [Environment and config](#environment-and-config)
- [Anti-patterns](#anti-patterns)

## Recommended layout

Single Next.js app (App Router):

```
app/
 (marketing)/ # route group - public pages
 layout.tsx
 page.tsx
 pricing/page.tsx
 (auth)/
 login/page.tsx
 signup/page.tsx
 (app)/ # authenticated app shell
 layout.tsx # auth guard + app chrome
 dashboard/page.tsx
 settings/page.tsx
 api/ # Route Handlers (webhooks, external)
components/
 ui/ # shadcn generated - do not edit
 {shared}/ # app-wide composed components
features/
 {feature}/
 components/
 actions.ts
 queries.ts
 schema.ts
 types.ts
lib/
 supabase/
 utils.ts # cn(), formatters
 analytics.ts
types/
 database.ts # supabase gen types
supabase/
 migrations/
```

Rules:
- `app/` routes stay thin - compose from `features/`.
- Shared UI that is not feature-specific → `components/`.
- Cross-feature imports go through `lib/` or explicit public feature APIs.

## Naming conventions

| Thing | Convention |
|---|---|
| Directories | `kebab-case` |
| React components | `PascalCase` files and exports |
| Hooks | `useCamelCase` |
| Server Actions | verb phrases: `createProject`, `updateProfile` |
| DB tables/columns | `snake_case` |
| TypeScript types | `PascalCase`; suffix `Input` for form DTOs |
| Env vars | `SCREAMING_SNAKE`; public prefixed `NEXT_PUBLIC_` |

## Feature boundaries

A feature owns:
- Its UI components
- Its Server Actions and queries
- Its Zod schemas and types
- Its tests (when present)

A feature does **not** import another feature's internals. Shared logic
elevates to `lib/`.

Public feature API surface:

```typescript
// features/billing/index.ts - explicit exports only
export { PricingTable } from "./components/pricing-table";
export { createCheckout } from "./actions";
```

## Scaling patterns

| Stage | Focus |
|---|---|
| MVP | Vertical slices, minimal abstractions, RLS + Server Actions |
| Growth | Feature folders, shared design system, query optimization |
| Scale | Read replicas, edge caching, job queue, observability |

Defer until needed:
- Microservices (monolith + Supabase scales far)
- Custom auth (Supabase Auth covers most SaaS)
- GraphQL (PostgREST + typed client suffices)
- State management library for server-fetched data

## Monorepo (Turbo)

See **`architecture-monorepo.md`** for full Turbo workspace setup, shared UI,
CI filters, and package boundaries. Single-app layout stays in this file.

Quick signal: `turbo.json` + `apps/` + `packages/` at repo root → load monorepo module.

## Environment and config

```
.env.local # gitignored secrets
.env.example # committed template, no values
```

Document every env var in `.env.example` with comment.

Config files:
- `next.config.ts` - images domains, redirects, `cacheComponents: true` on Next 16
- `proxy.ts` - auth session refresh only; keep fast (Next 15: `middleware.ts`)
- `components.json` - shadcn config; commit it

Never commit: `.env.local`, service role keys, Stripe secret keys.

## Anti-patterns

- God `utils/` folder with unrelated helpers
- Business logic in `page.tsx` files
- Circular imports between features
- Shared "hooks" folder that becomes a junk drawer
- API routes for everything (prefer Server Actions for app mutations)
- Premature abstraction layers ("repository pattern" over Supabase client)
- Mixing marketing and app layouts without route groups

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
