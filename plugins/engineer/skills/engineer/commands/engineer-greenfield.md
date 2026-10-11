---
description: Greenfield SaaS pipeline — architecture, design system, backend, enforcement, growth.
---

# /engineer-greenfield

Load engineer `SKILL.md` + `references/workflows.md` (Greenfield pipeline).

Product description follows this invocation.

## Phase 1 — Plan (`/engineer-plan` output)

Modules: system-architecture → architecture → design-system → backend-database → backend-auth → growth-funnels

Deliver: architecture, schema, tokens, activation event — **no code until approved**.

## Phase 2 — Build (after approval)

Order:

1. scaffold: Next.js + Tailwind v4 + shadcn/ui via `stack-rules.md` → Greenfield
   default stack (create-next-app + shadcn init/add), then de-genericize
   `--primary` / `--radius` / `--font-sans` before any pages
2. design-system tokens in `globals.css`
3. supabase migrations + RLS
4. auth (middleware, getUser pattern)
5. enforcement L2 (`/engineer-enforce`)
6. conversion-ui + frontend shell
7. growth instrumentation stubs

## Phase 3 — Ship prep

`/engineer-ship` when feature-complete.

## Scope guard

Greenfield ≠ rewrite existing app. Detect stack first — abort if wrong stack.
