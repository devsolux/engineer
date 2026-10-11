# TypeScript: types, APIs, and boundaries

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `backend-api.md` | Server Actions, Route Handlers |
| `backend-database.md` | Generated Supabase types |
| `python.md` | FastAPI peer services; OpenAPI → TS clients |
| `coding-principles.md` | Review standards |
| `api-data-flows.md` | Cross-service boundaries |

## Contents
- [Compiler standards](#compiler-standards)
- [Type design](#type-design)
- [Validation at boundaries](#validation-at-boundaries)
- [API handler patterns](#api-handler-patterns)
- [Shared types across stack](#shared-types-across-stack)
- [Error handling](#error-handling)
- [Anti-patterns](#anti-patterns)

## Compiler standards

Compiler update checked 2026-10-11: TypeScript 7.0.2 is current. Preserve the
consumer lockfile and compiler-API compatibility; do not force a major migration.
See `docs/verification-2026-10-11.md` in the skill package for the source ledger.

- `strict: true` always - no weakening for convenience
- `noUncheckedIndexedAccess` when project allows (safer arrays/records)
- `interface` for object shapes; `type` for unions, intersections, utilities
- Prefer `unknown` over `any`; narrow with Zod or type guards
- Discriminated unions for result types and state machines
- `const` assertions for config literals and route constants
- No `@ts-ignore` - fix or `@ts-expect-error` with reason

Import order: external → `@/` aliases → relative → type-only imports last.

## Type design

### Domain types vs DTOs

```typescript
// domain - internal, rich
interface Project {
 id: string;
 name: string;
 status: "draft" | "active" | "archived";
 ownerId: string;
 createdAt: Date;
}

// DTO - API/DB boundary, serializable
interface ProjectDto {
 id: string;
 name: string;
 status: "draft" | "active" | "archived";
 owner_id: string;
 created_at: string; // ISO from API/DB
}
```

Map at boundaries; don't leak DB snake_case into UI components.

### Result types (preferred over throw in Server Actions)

```typescript
type Result<T> =
 | { ok: true; data: T }
 | { ok: false; error: string; code?: string };
```

### Branded IDs (optional, high-value domains)

```typescript
type UserId = string & { readonly __brand: "UserId" };
type ProjectId = string & { readonly __brand: "ProjectId" };
```

Prevents passing wrong ID types - use when codebase already patterns this way.

## Validation at boundaries

**Every external input** gets Zod (or project's validator):

```typescript
import { z } from "zod";

export const createProjectSchema = z.object({
  name: z.string().min(1).max(100).trim(),
  description: z.string().max(2000).optional(),
});

export type CreateProjectInput = z.infer<typeof createProjectSchema>;
```

Boundaries:
- Server Actions - `safeParse` on FormData/JSON
- Route Handlers - parse body + query + params
- Webhook handlers - verify signature first, then Zod
- Env vars - `z.object` on `process.env` at startup

Share schemas between client (form) and server when possible - single source.

### Zod major version (3 vs 4)

| Policy | Detail |
|---|---|
| **One major per app** | Do not mix Zod 3 and Zod 4 in one package tree |
| Greenfield | Either 3 or 4 is fine - match team familiarity and deps |
| Existing repo | Stay on the installed major; upgrade as an intentional migration |
| APIs that differ | Prefer `safeParse`; re-check error shape helpers when upgrading |
| Monorepo | Align workspace packages on the same major |

COMPAT.md allows Zod v3 or v4. Agents must not "helpfully" upgrade Zod as a drive-by change.

## API handler patterns

### Server Action

```typescript
"use server";

export async function createProject(input: unknown): Promise<Result<ProjectDto>> {
 const parsed = createProjectSchema.safeParse(input);
 if (!parsed.success) return { ok: false, error: "Invalid input" };

 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { ok: false, error: "Unauthorized", code: "AUTH" };

 // ... mutate, return DTO
}
```

### Route Handler

```typescript
export async function POST(req: Request) {
 const body = await req.json().catch(() => null);
 const parsed = createProjectSchema.safeParse(body);
 if (!parsed.success) {
 return Response.json({ error: "Invalid input" }, { status: 400 });
 }
 // auth, mutate, return with correct status
}
```

Rules:
- Correct HTTP status codes (400 validation, 401 auth, 403 forbidden, 404, 409 conflict, 500 internal)
- Never leak stack traces in production responses
- Idempotency keys for payment/subscription webhooks

## Shared types across stack

Monorepo pattern:

```
packages/
 types/ # shared interfaces + Zod schemas
 db/ # Drizzle/Supabase generated types
apps/
 web/ # imports from @repo/types
services/
 api-rust/ # OpenAPI or protobuf contract → TS types via codegen
```

- **Contract first** for TS ↔ Rust: OpenAPI, protobuf, or shared JSON schema
- Generate TS types from contract; don't hand-sync Rust and TS structs
- Version API contracts; breaking changes need migration path

## Error handling

- Early returns over deep nesting
- Typed errors at domain layer; map to HTTP at edge
- Log server-side with context (userId, requestId); user sees safe message
- `console.log` not in production paths - use structured logger if project has one

## Anti-patterns

- `any` to silence the compiler
- Duplicated types between files (extract to shared package)
- Validating only on client
- `as SomeType` without runtime check on external data
- Enums for string unions (use literal unions + maps)
- Giant `types.ts` junk drawer - colocate with features
- Throwing strings instead of typed errors

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
