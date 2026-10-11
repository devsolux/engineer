# Frontend research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `frontend.md`, `frontend-performance.md`, `frontend-state.md`, `frontend-streaming.md`, `frontend-testing.md`

## Executive summary

2026 Next.js/React frontend standards converge on:

1. **Server Components by default** — client islands at leaves; serializable props only
2. **Field data Core Web Vitals** — LCP ≤2.5s, INP ≤200ms, CLS ≤0.1 (CrUX, not lab-only)
3. **State by purpose** — URL → Server/RSC → Query → Zustand for UI chrome (never API in Zustand)
4. **Granular Suspense** — stream independent sections; skeletons with fixed dimensions
5. **Testing pyramid** — Vitest unit + RTL integration + Playwright E2E (5–15 flows)
6. **shadcn forms** — RHF + Zod + Field/FieldGroup; `aria-invalid`, errors below field
7. **Compose perf** — vercel `react-best-practices` for 40+ React rules; engineer for architecture

---

## 1. React Server Components & client boundaries

**Sources**: react.dev (Server Components), nextjs.org (App Router), Vercel RSC docs,
patterns.dev (composition), `server-only` / `client-only` packages

### Decision framework

| Signal | Server Component | Client Component |
|---|---|---|
| Data fetch, DB, secrets | ✅ | ❌ |
| Static markup, links | ✅ | ❌ |
| useState, useEffect, events | ❌ | ✅ |
| Browser APIs | ❌ | ✅ |
| Third-party DOM libs | ❌ | ✅ |

### Patterns

**Children slot** — pass Server Component as child of Client wrapper:

```tsx
// client-dialog.tsx
"use client";
export function ClientDialog({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return open ? children : null;
}

// page.tsx (Server)
<ClientDialog>
  <ServerFetchedList /> {/* stays server */}
</ClientDialog>
```

**Serializable props only** — no functions, classes, or Date objects across boundary
(unless marked with React `use()` / Server Actions pattern).

**Package boundaries**:
- `import "server-only"` in modules that must never reach client bundle
- `import "client-only"` for browser-only utilities

### Anti-patterns (2026)

- `"use client"` on layout that only wraps children
- Fetch in `useEffect` when RSC works
- Entire page as Client Component
- Passing non-serializable props to client children

---

## 2. Core Web Vitals & performance

**Sources**: web.dev/vitals, Chrome UX Report, Next.js Image/Font docs,
Vercel Analytics, vercel-labs/agent-skills (react-best-practices)

### Thresholds (75th percentile field data)

| Metric | Good | Primary levers |
|---|---|---|
| LCP | ≤ 2.5s | Hero image priority, TTFB, fonts |
| INP | ≤ 200ms | Client JS, long tasks, hydration |
| CLS | ≤ 0.1 | Dimensions, fonts, skeletons |

### Image optimization

- `next/image` with explicit dimensions or `fill` + aspect container
- `priority` / preload on LCP element only (1–2 per page)
- `sizes` on every responsive image
- WebP/AVIF automatic; never raw `<img>` without dimensions

### Font optimization

- `next/font` self-hosted — eliminates layout shift from web font load
- CSS variables → `@theme` / shadcn tokens
- Limit families: sans + optional mono/display
- `display: "swap"`

### Bundle discipline

- Direct imports; no barrel files in hot paths
- `next/dynamic` for charts, editors, maps (fixed-height fallback)
- Defer third-party scripts (`afterInteractive`, `lazyOnload`)
- Audit `"use client"` file count periodically
- Server-side data — never duplicate fetch client-side

### Measurement

- **CrUX / Search Console** for field truth
- Lighthouse for regression detection, not sole gate
- `@next/bundle-analyzer` quarterly
- RUM via web-vitals or Vercel Analytics

---

## 3. State management (2026 consensus)

**Sources**: React 19 docs (useActionState, useOptimistic), TanStack Query docs,
nuqs, Zustand docs, Kent C. Dodds / TkDodo blog patterns

### Decision order

```
1. Server / RSC fetch
2. URL (searchParams / nuqs)
3. Server Actions + useActionState
4. TanStack Query (client server-state with refetch)
5. Zustand (ephemeral global UI)
6. useState (local)
7. Derived during render (never useEffect sync)
```

### Key rules

- **Never** store API responses in Zustand
- **URL** for filters, pagination, tabs — bookmarkable, server-readable
- **TanStack Query** when client needs refetch/polling/optimistic — not for static RSC data
- **useActionState** for Server Action form state (React 19)
- **useOptimistic** for optimistic UI with automatic rollback
- **Zustand selectors** — subscribe to slices, not whole store

### When NOT to add Redux

Greenfield 2026 apps rarely need Redux. Use when team already standardized on it
or complex client-only state machines require devtools/time-travel.

---

## 4. Streaming, Suspense, and boundaries

**Sources**: nextjs.org (loading.js, error.js), React Suspense docs,
Next.js 16 PPR / cacheComponents docs

### Granular Suspense

- Wrap each slow async section independently
- Static shell paints first; dynamic holes stream
- `Promise.all` for parallel independent fetches within a section

### loading.tsx vs Suspense

| Use loading.tsx | Use inline Suspense |
|---|---|
| Entire route segment async | Partial page can render early |
| Simple full-page spinner OK | Need section-level skeletons |

### error.tsx

- Must be Client Component
- `reset()` for retry
- Log server-side; user-friendly message only

### CLS from streaming

Skeleton height/width must match loaded content. Chart skeleton = chart height.
Table skeleton = same row count approximation.

### Next 16 PPR

`cacheComponents: true` → static shell + streamed dynamic. Don't wrap `<body>` in
Suspense. User-specific → Suspense hole, not whole-page dynamic.

---

## 5. Forms (shadcn + RHF + Zod)

**Sources**: ui.shadcn.com (forms, Field), react-hook-form docs, Zod docs,
Baymard form UX research (via design-patterns.md)

### Stack

```
schema.ts (Zod) → shared client + server
actions.ts (Server Action) → safeParse + auth + mutate
form.tsx (Client) → RHF + shadcn Field + Controller
```

### shadcn Field pattern (2026)

- `Field`, `FieldGroup`, `FieldLabel`, `FieldDescription`, `FieldError`
- `Controller` from RHF for controlled inputs
- `aria-invalid={!!fieldState.error}` on controls
- `data-invalid` on Field wrapper for styling
- Errors below field with icon + text (not color alone)

### Validation timing

- On blur for individual fields (22% error reduction — NN/g / form research)
- On submit for final gate
- Server re-validation always — client Zod is UX, not security

### Simple forms

For 1–2 fields with Server Action only: native form + `useActionState` — skip RHF.

---

## 6. Testing strategy

**Sources**: testing-library.com, Playwright docs, MSW docs, Kent C. Dodds testing pyramid

### Pyramid

| Layer | % effort | Tool |
|---|---|---|
| Unit | High volume, fast | Vitest |
| Integration | Forms, interactions | RTL + userEvent |
| E2E | Critical paths only | Playwright |

### Query priority

`getByRole` > `getByLabelText` > `getByPlaceholderText` >> `getByTestId`

### Mocking

- MSW for HTTP in integration tests
- Mock Supabase client for Server Action unit tests
- E2E against staging with seeded data or Supabase branch

### RSC testing

Don't render RSC in jsdom. Test extracted logic, or E2E the full path.

### CI minimum

Vitest + RTL on PR; Playwright smoke on staging; eslint-plugin-jsx-a11y.

---

## 7. Metadata, SEO, and social

**Sources**: nextjs.org (Metadata API), Google Search Central

### App Router Metadata

```tsx
// app/page.tsx or layout.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Product — Outcome in ≤60 chars",
  description: "Benefit-led description ≤155 chars",
  openGraph: {
    title: "...",
    description: "...",
    images: [{ url: "/og.png", width: 1200, height: 630 }],
  },
};
```

- `generateMetadata` for dynamic pages (blog, docs)
- One `<h1>` per page; logical heading hierarchy
- `robots.txt` + `sitemap.ts` for marketing sites
- JSON-LD for product/article when relevant (conversion-ui.md)

---

## 8. Internationalization (when needed)

**Sources**: next-intl, i18next docs

- Prefer `next-intl` for App Router (locale segment routing)
- Server Components can read locale and pass translated strings
- `Intl.DateTimeFormat` / `Intl.NumberFormat` — never raw `toLocaleDateString` without locale
- RTL layout testing when supporting Arabic/Hebrew

---

## 9. Module map → engineer references

| Research area | Reference module |
|---|---|
| RSC, components, forms overview | `frontend.md` |
| CWV, images, fonts, bundle | `frontend-performance.md` |
| State decision tree | `frontend-state.md` |
| Suspense, loading, error | `frontend-streaming.md` |
| Vitest, RTL, Playwright | `frontend-testing.md` |
| Tokens, layout | `design-system.md`, `design-patterns.md` |
| a11y | `design-accessibility.md` |
| React perf rules (40+) | vercel `react-best-practices` (compose) |

---

## Canonical sources

### React / Next.js
- https://react.dev/reference/rsc/server-components
- https://nextjs.org/docs/app/building-your-application/rendering/server-components
- https://nextjs.org/docs/app/api-reference/components/image
- https://nextjs.org/docs/app/building-your-application/optimizing/fonts
- https://nextjs.org/docs/app/building-your-application/routing/loading-ui-and-streaming
- https://nextjs.org/docs/app/api-reference/file-conventions/error

### Performance
- https://web.dev/vitals/
- https://github.com/vercel-labs/agent-skills (react-best-practices)

### State
- https://tanstack.com/query/latest/docs/framework/react/overview
- https://react.dev/reference/react/useActionState
- https://react.dev/reference/react/useOptimistic

### Testing
- https://testing-library.com/docs/react-testing-library/intro/
- https://playwright.dev/docs/intro
- https://mswjs.io/docs/

### Forms / UI
- https://ui.shadcn.com/docs/components/form
- https://ui.shadcn.com/docs/components/field
- https://react-hook-form.com/
- https://zod.dev/

### Design (cross-ref)
- `research/design-research.md`
