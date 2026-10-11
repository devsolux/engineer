# Frontend streaming: Suspense, loading, and error boundaries

**Last verified**: 2026-08-22 (Next.js 16.3.2 docs) · **Review cadence**: 3 months

App Router streaming model: static shell first, dynamic holes stream in.

## Persistent layouts & partial rendering

The pattern for "clicking a sidebar/nav item keeps the chrome mounted — only the content re-renders." Next.js name: **partial rendering** ("only the route segments that change on navigation re-render; shared segments are preserved," with client state kept).

- **Persistent chrome → `layout.tsx`, never `template.tsx`.** Layouts "preserve state, remain interactive, and do not rerender" across navigation. `template.tsx` gets a fresh key and **remounts every navigation** — use only when you *want* a reset (re-run enter animation). A sidebar in a `template.tsx` = the classic remount bug.
- **Route group `(folder)`** shares one layout across sibling routes **without changing URLs**: `app/(workspace)/layout.tsx` wraps `/studio`, `/score`, … — the `(name)` is stripped from the path. Move the routes in; URLs stay byte-identical.
- **Fetch shared shell data once in the layout** (session, entitlement, nav counts) — not per page. Nav active-state via `usePathname()` in a client nav (self-highlights; no per-page `active` prop, so the nav needn't re-render).
- **Content streams under the persistent shell** via each segment's `loading.tsx`/`<Suspense>` (below). Next 16 Cache Components: `loading.js` is a plain Suspense boundary; wrap any uncached/`cookies()` read the **layout** does in its *own* `<Suspense>` or it blocks navigation.
- **`next/dynamic`** for heavy client widgets in the content pane (editors/charts) — see `frontend-performance.md`.

Remounts the shell (kills persistence): rendering the sidebar per-page instead of in a shared `layout.tsx`; `template.tsx` for chrome; a `key` change or an unstable context provider (new object identity each render) high in the tree; driving views with `router.push`/state or `<a>` full reloads instead of `<Link>` + nested routes; navigating **across multiple root layouts** (forces a full page load — keep shared-shell routes under one root/group).

Docs: `getting-started/{layouts-and-pages,linking-and-navigating}`, `api-reference/file-conventions/{layout,template,route-groups,loading}`, `guides/lazy-loading`.

## Boundary types

| File | Scope | Server/Client |
|---|---|---|
| `loading.tsx` | Route segment fallback | Server |
| `error.tsx` | Route segment error UI | **Client** (`"use client"`) |
| `not-found.tsx` | 404 for segment | Server |
| `<Suspense>` | Inline async hole | Server (wraps async child) |

## Granular Suspense (preferred)

Wrap **each slow fetch**, not the whole page:

```tsx
// app/dashboard/page.tsx - Server Component
import { Suspense } from "react";
import { RevenueSkeleton } from "./skeletons";
import { RevenuePanel } from "./revenue-panel";
import { ActivityPanel } from "./activity-panel";

export default function DashboardPage() {
 return (
 <div className="grid gap-6 lg:grid-cols-2">
 <Suspense fallback={<RevenueSkeleton />}>
 <RevenuePanel />
 </Suspense>
 <Suspense fallback={<ActivitySkeleton />}>
 <ActivityPanel />
 </Suspense>
 </div>
 );
}
```

Benefits:
- Fast shell paints immediately
- Independent sections stream as data arrives
- One slow query doesn't block the whole page

## loading.tsx - when to use

Use for **route-level** loading when the entire segment is async and you don't need partial UI.

Don't use as a substitute for granular Suspense when parts of the page can render early.

## error.tsx requirements

```tsx
"use client";

export default function Error({
 error,
 reset,
}: {
 error: Error & { digest?: string };
 reset: () => void;
}) {
 return (
 <div role="alert" className="rounded-lg border border-border bg-card p-6">
 <h2 className="text-lg font-semibold">Something went wrong</h2>
 <p className="text-muted-foreground mt-2">{error.message}</p>
 <button onClick={reset} className="mt-4">
 Try again
 </button>
 </div>
 );
}
```

- Must be Client Component
- `reset()` re-renders the segment - use for retry
- Log to monitoring in `useEffect` - don't expose stack to users in prod

## Skeleton rules (CLS)

Skeletons must **match final layout dimensions**:

```tsx
export function RevenueSkeleton() {
 return (
 <div className="h-[320px] rounded-lg border border-border bg-muted/50 animate-pulse" />
 );
}
```

- Fixed height/width on chart/table skeletons
- Same grid columns as loaded state
- Avoid skeleton → content height jump

## Parallel routes + intercepting (optional)

Use when modals/overlays need URL state without full navigation:

```
app/
 @modal/
 (.)photos/[id]/page.tsx # intercept - modal overlay
 photos/[id]/page.tsx # full page on direct visit
```

Pattern: shareable modal URLs, back button closes modal.

## Next 16 + PPR notes

With `cacheComponents: true`:
- Static shell streams immediately
- Dynamic holes resolve via Suspense
- Don't wrap entire `<body>` in Suspense
- User-specific content → Suspense boundary, not `connection()` for whole page

See `data-layer.md` for `use cache` placement.

## Streaming anti-patterns

- Sidebar/chrome rendered per-page instead of a shared `layout.tsx` (remounts on every nav; see Persistent layouts above)
- `template.tsx` for persistent chrome (remounts every navigation)
- One giant Suspense around entire page
- Skeleton with no reserved dimensions (CLS)
- `loading.tsx` when partial render is possible
- Fetching sequentially when parallel works (`Promise.all`)
- Showing blank screen instead of skeleton during stream
- Client-side `useEffect` fetch when RSC + Suspense works

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
