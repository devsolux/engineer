# Backend API: Server Actions, Route Handlers, and gates

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

Choose the simplest path that meets the client and integration needs.

## Contents
- [Decision tree](#decision-tree)
- [Server Actions](#server-actions)
- [Route Handlers](#route-handlers)
- [Data Access Layer (DAL)](#data-access-layer-dal)
- [Enforcement](#enforcement)
- [Anti-patterns](#anti-patterns)

## Decision tree

```
Browser form mutation, same app?
 └─ YES → Server Action (default)

External client, webhook, mobile, third-party?
 └─ YES → Route Handler (`app/api/**/route.ts`)

High-throughput / streaming / non-Next runtime?
 └─ YES → Rust service (see rust.md) or Supabase Edge Function

Read-only data for RSC?
 └─ YES → Server Component fetch (not an API route)
```

## Server Actions

**Default for app mutations.** Callable via POST with action ID - treat as public.

### Five gates (every action)

1. **Rate limit** - sensitive actions (auth, billing, delete, contact)
2. **Validate** - Zod `safeParse` on all input
3. **Authenticate** - `getUser()` or equivalent
4. **Authorize** - ownership/role check (RLS + explicit for cross-user)
5. **Mutate + invalidate** - DB write → `updateTag` / `revalidatePath`

```typescript
"use server";

import { updateTag } from "next/cache";
import { createClient } from "@/lib/supabase/server";
import { createProjectSchema } from "./schema";

export async function createProject(
 input: unknown
): Promise<Result<ProjectDto>> {
 const parsed = createProjectSchema.safeParse(input);
 if (!parsed.success) return { ok: false, error: "Invalid input" };

 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { ok: false, error: "Unauthorized", code: "AUTH" };

 const { data, error } = await supabase
 .from("projects")
 .insert({ ...parsed.data, user_id: user.id })
 .select("id, name, status, created_at")
 .single();

 if (error) return { ok: false, error: error.message };

 updateTag("projects"); // read-your-own-writes - Server Actions only
 return { ok: true, data: mapProject(data) };
}
```

### useActionState (simple forms)

```typescript
"use server";

export async function createProjectAction(
 _prev: ActionState | null,
 formData: FormData
): Promise<ActionState> {
 return createProject(Object.fromEntries(formData));
}
```

### CSRF / origins (Server Actions)

Next.js provides structural CSRF (POST-only + Origin vs Host or `X-Forwarded-Host`).
**Not a substitute for auth, Zod, or rate limits.** Treat every action as a public POST endpoint.

```js
// next.config.ts / next.config.mjs
const nextConfig = {
 experimental: {
 serverActions: {
 // Needed when a proxy/CDN does not forward the public host in X-Forwarded-Host
 allowedOrigins: ["myapp.com", "*.myapp.com"],
 },
 },
};
```

| Control | Detail |
|---|---|
| Framework | POST-only + Origin/Host match (default) |
| Proxies | Forward the public host in `X-Forwarded-Host`, else list it in `serverActions.allowedOrigins` |
| Cookies | Session cookies `SameSite=Lax` or `Strict` (auth module) |
| App code | `getUser()` + authorization + Zod + rate limit on every mutate |
| Route Handlers | No free CSRF shield - verify Origin or use non-cookie auth |

**Hardening notes (2026):**

- Keep **Next.js patched** - CSRF validation bugs have appeared around opaque/`null` origins (sandboxed iframes; CVE-2026-27978, fixed in 16.1.7). Do not assume "we use Server Actions" equals forever-safe CSRF.
- Do not treat a missing Origin as "same-site" - Next.js lets an Origin-less action request through with a warning.
- Prefer short-lived sessions; re-auth for delete-account / billing changes (`compliance-privacy.md`, `billing-stripe.md`).

### Rate limiting

Order for authenticated actions: **auth → rate limit → validate → mutate**

```typescript
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";

const limiter = new Ratelimit({
 redis: Redis.fromEnv(),
 limiter: Ratelimit.slidingWindow(10, "1 m"),
});

// In action:
const { success } = await limiter.limit(`create-project:${user.id}`);
if (!success) return { ok: false, error: "Too many requests", code: "RATE_LIMIT" };
```

Rate-limit by user ID (authenticated) or IP (anonymous).

Copy-ready helper: **`templates/lib/rate-limit.ts`** (`rateLimit` / `rateLimitUser` - scanner-friendly names).

Order reminder: **auth → rate limit → Zod → mutate**. Under `engineer-scan --strict`, missing limiters on sensitive actions fail CI (`enforcement-rules.md`).

## Route Handlers

Use for: webhooks, mobile clients, public REST, cache revalidation endpoints.

```typescript
// app/api/projects/route.ts
import { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { createProjectSchema } from "@/features/projects/schema";

export async function POST(req: NextRequest) {
 const body = await req.json().catch(() => null);
 const parsed = createProjectSchema.safeParse(body);
 if (!parsed.success) {
 return Response.json({ error: "Invalid input" }, { status: 400 });
 }

 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) {
 return Response.json({ error: "Unauthorized" }, { status: 401 });
 }

 const { data, error } = await supabase
 .from("projects")
 .insert({ ...parsed.data, user_id: user.id })
 .select()
 .single();

 if (error) {
 const status = error.code === "23505" ? 409 : 500; // unique_violation → Conflict
 return Response.json({ error: status === 409 ? "Conflict" : "Internal error" }, { status });
 }

 return Response.json(data, { status: 201 });
}
```

### HTTP status codes

| Code | When |
|---|---|
| 400 | Validation failed |
| 401 | Not authenticated |
| 403 | Authenticated but forbidden |
| 404 | Resource not found |
| 409 | Conflict (duplicate, state) |
| 422 | Semantic validation |
| 429 | Rate limited |
| 500 | Internal (log details; safe message to client) |

### Cache invalidation in Route Handlers

**Cannot use `updateTag`** - Server Actions only. Use `revalidateTag`:

```typescript
import { revalidateTag } from "next/cache";

export async function POST(req: Request) {
 // webhook processed...
 revalidateTag("projects", "max"); // { expire: 0 } when stale reads are not acceptable
 return Response.json({ ok: true });
}
```

## Data Access Layer (DAL)

Centralize auth + queries - don't scatter checks:

```typescript
// lib/dal/projects.ts
import "server-only";
import { cache } from "react";
import { createClient } from "@/lib/supabase/server";

export const getCurrentUser = cache(async () => {
 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 return user;
});

export async function getProjectsForUser() {
 const user = await getCurrentUser();
 if (!user) throw new Error("Unauthorized");

 const supabase = await createClient();
 const { data, error } = await supabase
 .from("projects")
 .select("id, name, status, updated_at")
 .eq("user_id", user.id)
 .order("updated_at", { ascending: false });

 if (error) throw error;
 return data;
}
```

Mark DAL modules with `import "server-only"`.

## Enforcement

| Rule | Tool |
|---|---|
| RLS on new tables | `scripts/check-rls-migration.sh` |
| getUser on mutations | `engineer-scan --strict` |
| No updateTag in handlers | `engineer-scan --backend` |
| Zod on inputs | Vitest + code review |
| Rate limits | Integration tests on auth/billing actions |

See `enforcement-rules.md` for the Server Action auth grep and `enforcement.md` for the CI workflow.

| Concern | Server Action | Route Handler |
|---|---|---|
| Form mutations | ✅ default | possible |
| Progressive enhancement | ✅ native | manual |
| External/webhook clients | ❌ | ✅ |
| `updateTag` (immediate) | ✅ | ❌ use `revalidateTag(tag, { expire: 0 })` |
| OpenAPI / REST contract | awkward | ✅ |
| File upload | ✅ with limits | ✅ |

## Anti-patterns

- Server Action without auth check
- Route Handler returning 200 on validation failure
- `updateTag` in Route Handler (runtime error)
- Leaking stack traces in JSON responses
- God `/api` route doing everything
- Validating only on client
- Sequential awaits for independent reads
- Sensitive actions without rate limiting
- Inline actions closing over secrets (use separate `"use server"` files)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
