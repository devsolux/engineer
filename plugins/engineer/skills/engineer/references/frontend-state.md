# Frontend state: what goes where (2026)

**Last verified**: 2026-07-12 · **Review cadence**: 3 months

| Related | When |
|---|---|
| `data-layer.md` | Server fetch, cache tags |
| `frontend.md` | RSC vs client boundaries |
| `frontend-performance.md` | URL state vs client stores |

Stop forcing all state into one store. Use the **decision tree** below.

## Decision tree

```
Is it from the server/API?
 └─ YES → RSC fetch OR TanStack Query (if client refetch needed)
 NEVER sync server data into Zustand

Should it survive refresh or be shareable?
 └─ YES → URL searchParams (nuqs for type-safe)

Is it form input/validation?
 └─ YES → React Hook Form + Zod
 OR useActionState for simple Server Actions

Is it ephemeral global UI (sidebar, theme, modal)?
 └─ YES → Zustand (minimal store) OR React context if rare updates

Is it local to one component?
 └─ YES → useState / useReducer

Is it derived from props or other state?
 └─ YES → compute during render - no useEffect sync
```

## Server state

**Default in App Router**: fetch in Server Component.

Use **TanStack Query** when the project already has it AND you need:
- Client refetch, polling, infinite scroll
- Optimistic updates with rollback
- Shared cache across client navigations

```typescript
// Query key includes URL params when filters live in searchParams
const { data } = useQuery({
 queryKey: ["projects", category, page],
 queryFn: () => fetchProjects({ category, page }),
});
```

Rules:
- Don't duplicate RSC-fetched data in Query unless client needs live updates
- Invalidate via `queryClient.invalidateQueries` after Server Action mutations
- Never store API responses in `useState` without Query/cache layer

## URL state

Filters, pagination, tabs, sort - **prefer URL**:

```typescript
// With nuqs (if in project)
const [page, setPage] = useQueryState("page", parseAsInteger.withDefault(1));

// Native App Router - available in RSC via searchParams prop
export default async function Page({
 searchParams,
}: {
 searchParams: Promise<{ page?: string }>;
}) {
 const { page = "1" } = await searchParams;
 // ...
}
```

Benefits: bookmarkable, shareable, back-button works, server-readable.

## Form state

| Complexity | Tool |
|---|---|
| Simple Server Action form | `useActionState` + native fields |
| Multi-field, client validation | React Hook Form + Zod + shadcn Field |
| Wizard / dynamic arrays | RHF + `useFieldArray` + Zod |

Server Action pattern with `useActionState` (React 19):

```tsx
"use client";

import { useActionState } from "react";
import { createProject } from "./actions";

export function CreateProjectForm() {
 const [state, action, pending] = useActionState(createProject, null);
 return (
 <form action={action}>
 {/* fields */}
 {state?.error && <p role="alert">{state.error}</p>}
 <button disabled={pending}>Create</button>
 </form>
 );
}
```

## Global UI state (Zustand)

```typescript
import { create } from "zustand";

interface UiStore {
 sidebarOpen: boolean;
 toggleSidebar: () => void;
}

export const useUiStore = create<UiStore>((set) => ({
 sidebarOpen: true,
 toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}));

// In component - selector prevents unnecessary re-renders
const sidebarOpen = useUiStore((s) => s.sidebarOpen);
```

Use `persist` middleware only for user preferences (theme), not server data.

## React 19+ native patterns

- **`useActionState`** - form submission state from Server Actions
- **`useOptimistic`** - optimistic UI with automatic rollback
- **`use()`** - read promises in render (Client Components)

Prefer native patterns before adding libraries when they fit.

## Anti-patterns

- `useEffect` + `fetch` + `setState` for initial data (use RSC or Query)
- Storing server data in Zustand/Redux
- Context for high-frequency updates (re-renders all consumers)
- Redux on greenfield 2026 apps without team requirement
- Syncing URL ↔ useState for filters (pick URL as source of truth)
- `useEffect` to derive state from props

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
