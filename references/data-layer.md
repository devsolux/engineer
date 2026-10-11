# Data layer: queries, cache, real-time

**Last verified**: 2026-08-19 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `backend-api.md` | Mutations, revalidation |
| `frontend-state.md` | Client cache vs URL state |
| `frontend-streaming.md` | Suspense with async data |
| `backend-database.md` | RLS affects queries |

## Contents
- [Query patterns](#query-patterns)
- [Caching model](#caching-model)
- [React Query (when present)](#react-query-when-present)
- [Real-time](#real-time)
- [Error and loading states](#error-and-loading-states)
- [Anti-patterns](#anti-patterns)

## Query patterns

**Server-first fetching** in RSC:

```typescript
import { createClient } from "@/lib/supabase/server";

export async function getProjects(userId: string) {
 const supabase = await createClient();
 const { data, error } = await supabase
 .from("projects")
 .select("id, name, status, updated_at")
 .eq("user_id", userId)
 .order("updated_at", { ascending: false });

 if (error) throw error;
 return data;
}
```

Rules:
- Select only needed columns - no `select("*")` in production hot paths.
- Push filters to the database; do not fetch-all-then-filter in JS.
- Use `.single()` when expecting one row; handle `PGRST116` (not found).
- Paginate: `.range(from, to)` or cursor on `created_at` / `id`.
- Wrap repeated server reads in `React.cache()` for per-request dedup.

Parallel independent queries:

```typescript
const [projects, profile] = await Promise.all([
 getProjects(userId),
 getProfile(userId),
]);
```

## Caching model

Greenfield Next 16 uses **Cache Components**: `cacheComponents: true` plus explicit `"use cache"`. Do not teach implicit App Router fetch caching as the default.

Four layers (know which one you're debugging):

1. **Request memoization** - `React.cache()`, same render pass
2. **Data cache** - `use cache` + `cacheLife` + `cacheTag` (Next 16 Cache Components)
3. **Full route cache** - static shell from build/prerender (PPR with `cacheComponents`)
4. **Client router cache** - stale time on client navigations

### use cache placement

Place `'use cache'` on **data functions or leaf components**, not page orchestrators.

```typescript
import { cacheLife, cacheTag } from "next/cache";

export async function getPublicPricing() {
 "use cache";
 cacheLife("hours");
 cacheTag("pricing");

 const supabase = await createClient();
 const { data, error } = await supabase.from("plans").select("id, name, price");
 if (error) throw error;
 return data;
}
```

When to use `use cache`:
- Read-heavy data shared across users (public content, pricing, docs)
- Expensive aggregation that tolerates staleness

When NOT to use `use cache`:
- User-specific data tied to cookies/session (read auth outside, pass as arg)
- Real-time or must-be-fresh mutations
- Inside scope that calls `cookies()` or `headers()`

### Invalidation (Next.js 16) - critical split

| Function | Context | Behavior |
|---|---|---|
| `updateTag("tag")` | **Server Actions only** | Immediate expiry (read-your-own-writes) |
| `revalidateTag("tag", profile)` | Route Handlers, webhooks | Stale-while-revalidate |
| `revalidatePath("/path")` | Either | Page-level freshness |

**Never call `updateTag` in Route Handlers** - runtime error.

Maintain a **cache tag registry** as the app grows (template: **`templates/lib/cache-tags.ts`** - CODEOWNERS that file):

```typescript
// lib/cache-tags.ts
export const CACHE_TAGS = {
 projects: (userId: string) => `projects:${userId}`,
 project: (id: string) => `project:${id}`,
 pricing: "pricing",
} as const;
```

Always set explicit `cacheLife` when using `use cache`.

### cacheLife presets (practical)

| Profile | Use for |
|---|---|
| `seconds` / short | Near-live dashboards that still tolerate brief stale |
| `minutes` | User lists that revalidate on mutation via `updateTag` |
| `hours` | Pricing, public marketing content, docs index |
| `days` / `max` | Rarely changing public content; pair `max` with on-demand tags |

Rules (Next 16 Cache Components):
- Enable `cacheComponents: true` before relying on `'use cache'`
- Uncached async UI needs **Suspense** (or `'use cache'`) - do not leave bare async holes in the shell
- Read `cookies()` / `headers()` **outside** cached scopes; pass values as arguments
- Prefer tag invalidation over long TTL for multi-tenant data

Template registry: `templates/lib/cache-tags.ts` (add org/content/vector tags as features grow).

## React Query (when present)

Use when the project already has `@tanstack/react-query`:

- Client-side refetch, optimistic updates, infinite scroll
- Server still owns initial data (prefetch in RSC, dehydrate if needed)
- Query keys: `["projects", userId]`, `["project", id]`

Do not introduce React Query in a project that doesn't use it unless
client refetch complexity justifies the dependency.

## Real-time

Supabase Realtime for:
- Live dashboards, notifications, collaborative presence
- Subscribe in **client components only**
- Filter channels: `schema: 'public', table: 'messages', filter: 'room_id=eq.x'`
- Unsubscribe on unmount

### Auth and RLS for Realtime

| Rule | Detail |
|---|---|
| Same JWT as data API | Browser client with user session; not service role |
| RLS still applies | Channel filter is not a security boundary alone |
| Private channels | Prefer topic design that includes `org_id` / row filters the user can already `select` |
| Presence | Do not put secrets or PII in presence payloads |
| Token refresh | Resubscribe on auth state change (sign-in/out) |

```typescript
// Client only - illustrative
useEffect(() => {
 const supabase = createClient();
 const channel = supabase
 .channel(`org:${orgId}:messages`)
 .on(
 "postgres_changes",
 { event: "INSERT", schema: "public", table: "messages", filter: `org_id=eq.${orgId}` },
 (payload) => onInsert(payload.new),
 )
 .subscribe();
 return () => {
 void supabase.removeChannel(channel);
 };
}, [orgId]);
```

### Private Broadcast / Presence authorization

Postgres Changes inherit table RLS. **Broadcast and Presence** need explicit auth:

1. RLS policies on `realtime.messages` (Supabase Realtime Authorization)
2. Client: `config: { private: true }` on the channel
3. Sensitive apps: prefer project setting that disallows open public channels

```typescript
const channel = supabase.channel(`room:${orgId}`, {
 config: { private: true },
});
// policies on realtime.messages control join/send for that topic
```

Do not use Realtime when polling or RSC revalidation suffices.
Never open a Realtime subscription with the service role in the browser.
Never treat a public broadcast topic name as a secret.

## Error and loading states

Every async surface needs three states:

| State | UI |
|---|---|
| Loading | Skeleton matching final layout (not spinner-only for pages) |
| Empty | Helpful message + primary action ("Create your first project") |
| Error | Human message + retry action; log details server-side |

In RSC: use `error.tsx` and `loading.tsx` per route segment.
Suspense boundaries around slow subtrees, not the entire page unless intentional.

## Anti-patterns

- Sequential `await` for independent queries
- Fetching in `useEffect` what RSC could fetch on the server
- No pagination on unbounded lists
- Caching user-specific data in `use cache` without passing userId as key
- `select("*")` on wide tables
- Calling `updateTag` in Route Handler (use `revalidateTag`)
- Missing error boundary on data-heavy routes
- Realtime subscription without cleanup

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
