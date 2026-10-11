# Frontend: components, RSC, forms, and submodules

**Last verified**: 2026-08-21 · **Review cadence**: 3 months

Router for frontend implementation. Deep dives live in sibling modules:

| Topic | Module |
|---|---|
| Core Web Vitals, images, fonts, bundle | `frontend-performance.md` |
| State decision tree (URL, Query, Zustand) | `frontend-state.md` |
| Suspense, loading.tsx, error.tsx | `frontend-streaming.md` |
| Persistent layout / sidebar stays on nav / partial rendering / route groups | `frontend-streaming.md` |
| Vitest, RTL, Playwright, MSW | `frontend-testing.md` |
| next-intl, locales, hreflang | `frontend-i18n.md` |
| Storybook (optional) | `storybook-dx.md` |
| Tokens, layout, forms UX | `design-system.md`, `design-patterns.md` |
| Aesthetic, taste, de-generic UI | `design-taste.md` |
| React perf rules (40+) | vercel `react-best-practices` (compose) |

Full research corpus: `research/frontend-research.md`

## Contents
- [Component architecture](#component-architecture)
- [Server vs client](#server-vs-client)
- [RSC decision checklist](#rsc-decision-checklist)
- [Forms and validation](#forms-and-validation)
- [Metadata and SEO](#metadata-and-seo)
- [Styling and tokens](#styling-and-tokens)
- [Performance (summary)](#performance-summary)
- [Accessibility](#accessibility)
- [Anti-patterns](#anti-patterns)

## Component architecture

- **One component, one job.** Split when a file exceeds ~150 lines or mixes
 data fetching with heavy interactivity.
- **Colocate by feature**, not by type:
 ```
 features/billing/
 components/
 actions.ts
 queries.ts
 schema.ts
 types.ts
 ```
- **Composition over configuration.** Prefer compound components (Card +
 CardHeader + CardContent) over mega-props.
- **Named exports** for components and hooks. Default exports only for
 `page.tsx` / `layout.tsx` / `route.ts` where Next requires them.
- **Product abstractions** over raw shadcn: `AppButton`, `AppDialog` wrapping
 `components/ui/*` - never edit generated shadcn files for one-offs.

## Server vs client

Default tree:

```
Server Layout (auth, data shell)
 └─ Server Page (fetch, pass serializable props)
 └─ Client Island (form, modal, chart, drag-drop)
```

Add `"use client"` when the component uses:
- `useState`, `useEffect`, `useReducer`, browser event handlers
- Browser APIs (`window`, `localStorage`, `ResizeObserver`)
- Third-party libs that require DOM (`react-dropzone`, some chart libs)

Do **not** add `"use client"` for:
- Static markup, links, server-fetched lists rendered as HTML
- Components that only accept callbacks from a parent client component

Push client boundaries **down** the tree. Fetch on the server, pass data down.

### Children slot pattern

Pass Server Components as children of a Client wrapper - keeps data on server:

```tsx
"use client";
export function ModalShell({ children }: { children: React.ReactNode }) {
 // client interactivity only
 return <dialog open>{children}</dialog>;
}
```

### Package guards

- `import "server-only"` in modules with secrets/DB - fails if imported client-side
- `import "client-only"` for browser-only utilities

## RSC decision checklist

Before adding `"use client"`, ask:

1. Can this fetch run in a Server Component parent?
2. Can interactivity live in a leaf while parent stays server?
3. Are props serializable (no functions/classes/Date)?
4. Does a Server Action replace client fetch + mutation?
5. Will this increase client bundle meaningfully?

If yes to 1-4, keep server. See `frontend-streaming.md` for async boundaries.

## Forms and validation

Standard stack: **Zod + Server Action + RHF + shadcn Field** (complex) or
**Zod + useActionState** (simple).

```typescript
// schema.ts - shared client + server
import { z } from "zod";

export const profileSchema = z.object({
 name: z.string().min(1).max(100),
 email: z.string().email(),
});

export type ProfileInput = z.infer<typeof profileSchema>;
```

```typescript
// actions.ts - Server Action
"use server";

import { profileSchema } from "./schema";
import { createClient } from "@/lib/supabase/server";

export async function updateProfile(formData: FormData) {
 const parsed = profileSchema.safeParse(Object.fromEntries(formData));
 if (!parsed.success) return { error: parsed.error.flatten() };

 const supabase = await createClient();
 const { data: { user } } = await supabase.auth.getUser();
 if (!user) return { error: "Unauthorized" };

 // ... mutate
}
```

### shadcn Field + RHF (multi-field)

```tsx
"use client";

import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
 Field, FieldError, FieldGroup, FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { profileSchema, type ProfileInput } from "./schema";

export function ProfileForm() {
 const form = useForm<ProfileInput>({
 resolver: zodResolver(profileSchema),
 mode: "onBlur",
 });

 return (
 <form onSubmit={form.handleSubmit(onSubmit)}>
 <FieldGroup>
 <Controller
 name="email"
 control={form.control}
 render={({ field, fieldState }) => (
 <Field data-invalid={!!fieldState.error}>
 <FieldLabel htmlFor="email">Email</FieldLabel>
 <Input
 {...field}
 id="email"
 type="email"
 aria-invalid={!!fieldState.error}
 />
 <FieldError errors={[fieldState.error]} />
 </Field>
 )}
 />
 </FieldGroup>
 </form>
 );
}
```

Form UX rules (see `design-patterns.md`):
- Labels above fields - always visible, not placeholder-only
- Validate on blur; errors below field with icon + text
- Zod at every boundary - client validation is UX, server is security
- Never block paste on inputs
- Optimistic UI only when rollback path is clear (`useOptimistic`)

State placement: see `frontend-state.md`.

## Metadata and SEO

See **`seo-metadata.md`** for metadata API, sitemap, JSON-LD, hreflang, and
canonical URLs. For i18n metadata, also load **`frontend-i18n.md`**.

Quick rules: one `<h1>` per page; `Intl.*` for dates/numbers - never bare
`toLocaleDateString()` in components.

## Styling and tokens

See `design-system.md` for tokens, `design-patterns.md` for layout, `design-taste.md` before new pixels.

- **Greenfield default**: Tailwind v4 + shadcn/ui (`stack-rules.md` → Greenfield
 default stack); build on wrapped shadcn primitives, not hand-rolled components.
- **MANDATORY**: semantic theme tokens from `globals.css` / `@theme`.
- **FORBIDDEN**: hardcoded Tailwind colors (`text-red-500`, `bg-gray-100`, `bg-indigo-*`).
- `className` is for layout/spacing/responsive - not for overriding component colors.
- Restyle shadcn at the token layer (`--primary`, `--radius`, `--font-sans`).
- Mobile-first breakpoints. Test 320, 375, 768, 1280.
- Flex + `gap-*`; no `space-y-*`.
- New or redesigned surfaces: named tone + signature (`design-taste.md`) before JSX.

For visual taste beyond tokens, load `design-taste.md` and run `unmachined` on the UI surface.

## Performance (summary)

Full checklist: `frontend-performance.md`. Compose vercel `react-best-practices`.

Priority order:

1. Parallelize server fetches (`Promise.all`).
2. RSC default - minimal client JS (INP).
3. LCP: `next/image` + `priority` on hero; `next/font` self-hosted.
4. CLS: explicit dimensions; skeletons match final layout.
5. Direct imports; `next/dynamic` for heavy client libs.
6. Lists >50 items: virtualize (`virtua` or `content-visibility: auto`).
7. Animate `transform` and `opacity` only; honor `prefers-reduced-motion`.

Field data (CrUX) beats lab-only Lighthouse for pass/fail.

## Accessibility

See `design-accessibility.md` for full WCAG 2.2 AA checklist.

- Every input has a `<label>` or `aria-label`.
- Focus rings visible (`focus-visible:ring-*`); never naked `outline-hidden`.
- Dialog/Sheet/Drawer: Title required; trap focus; restore on close.
- Icon-only buttons: `aria-label`.
- Color is never the only signal - add text/icon/pattern.
- Touch targets ≥44px where possible.

## Anti-patterns

- `"use client"` on layouts that only wrap children
- Prop drilling 5+ levels for data (fetch where needed; RSC memoizes)
- `useEffect` to sync props → state
- Raw `fetch` in client components when Server Action or RSC suffices
- API data in Zustand (see `frontend-state.md`)
- One giant Suspense around whole page (see `frontend-streaming.md`)
- Skeleton without reserved dimensions (CLS)
- Inline styles for things Tailwind tokens handle
- Shipping Inter + indigo + three feature cards as a "design"
- `<div onClick>` instead of `<button>` / `<Link>`
- Form inputs without labels
- Hardcoded `toLocaleDateString` - use `Intl.DateTimeFormat`
- Testing implementation details instead of user behavior (see `frontend-testing.md`)

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
