# Stack rules (condensed)

**Last verified**: 2026-08-21 · **Review cadence**: 3 months

Framework-correctness for Next.js, Tailwind v4, shadcn/ui, React 19.
Python services: see **`python.md`** (uv/ruff/FastAPI peer language).
For the full catalog (grep scan, cacheLife table, 10-second slop grep),
load `unmachined/references/stack-rules.md` when available.

## Version detection

Confirm from `package.json` and CSS/config before applying rules.
See `project-detect.md`.

## Greenfield default stack (binding)

A new Next.js app built by engineer ships **Tailwind v4 + shadcn/ui by default** —
not on request. UI is built on shadcn primitives (wrapped, per de-genericization
below), never hand-rolled CSS component libraries. Skipping either requires an
explicit user decision or a project pin — state it and flag it. Existing
codebases are the opposite case: follow project truth (version-conflict rule in
`project-detect.md`); never retrofit this default into a repo that deliberately
uses another styling system.

Scaffold (pnpm per toolchain policy; any flag ⇒ non-interactive with
recommended defaults):

```bash
pnpm create next-app@latest <app> --ts --tailwind --eslint --app --src-dir \
  --import-alias "@/*" --use-pnpm
cd <app>
pnpm add -D shadcn@4.18.0            # pin current; then run the locked local CLI
pnpm exec shadcn init                # components.json + @theme wiring; -b radix|base|aria
pnpm exec shadcn add button input label field card dialog dropdown-menu sonner
```

Commands are version-sensitive: past this module's review cadence, or when a
flag errors, re-verify against `--help` / current official docs before
asserting them — never patch from memory. Immediately after init, de-genericize
(`--primary`, `--radius`, `--font-sans` off stock — section below) before
building pages.

## Tailwind v4 essentials

| Banned (v3) | Use (v4) |
|---|---|
| `@tailwind base/components/utilities` | `@import "tailwindcss"` |
| `tailwind.config.js` theme | `@theme { }` in CSS |
| `bg-opacity-50` | `bg-red-500/50` |
| `bg-gradient-to-r` | `bg-linear-to-r` |
| `!flex` | `flex!` |
| `space-x-*` / `space-y-*` | `flex` + `gap-*` |
| `outline-none` | `outline-hidden` + focus-visible replacement |
| `w-10 h-10` | `size-10` |

Define brand tokens in `@theme`, not raw hex in components.
Semantic classes only: `bg-primary`, `text-muted-foreground`.

Greenfield CSS starts with `@import "tailwindcss";` as the first line. If Turbopack HMR misses new classes until restart, add explicit globs:

```css
@import "tailwindcss";
@source "../app/**/*.{ts,tsx}";
@source "../components/**/*.{ts,tsx}";
```

Use `@tailwindcss/postcss` in `postcss.config.mjs`. Do not leave a v3 `tailwind.config.js` unless imported via `@config`.

## Next.js 16 / App Router essentials

- Greenfield is Next **16.x** (LTS). Detect 15.x and keep its conventions until a deliberate upgrade.
- Server Components default. `"use client"` only when required.
- Request boundary: `proxy.ts` exporting `proxy` (Next 16). Keep `middleware.ts` only when the detected major is 15.
- Parallelize independent fetches: initiate all, then `Promise.all`.
- Cache Components: set `cacheComponents: true`; place `"use cache"` on data functions or leaf components; no `cookies()`/`headers()` inside `use cache`.
- Colocate by feature; route groups `(marketing)` for layout variants.
- Authenticate Server Actions like public API endpoints.

## Python peer (services)

When `pyproject.toml` / `uv.lock` / FastAPI is detected, apply `python.md` defaults:

| Prefer | Avoid (greenfield) |
|---|---|
| uv + `uv.lock` | Poetry / pip-freeze as sole lock |
| ruff format+check | Black + isort + flake8 |
| basedpyright CI | mypy-only as sole gate |
| FastAPI lifespan | `@app.on_event` |
| PyJWT + `algorithms=` | python-jose |
| Taskiq/Temporal for durable work | `BackgroundTasks` for payments |

Language split: **TS** = UI/session/CRUD · **Python** = AI/workers/OpenAPI services · **Rust** = measured hot paths.

## shadcn de-genericization

Change all three before building:

| Dial | Stock (avoid) | Move to |
|---|---|---|
| `--primary` | muted indigo/zinc | one brand accent, used sparingly |
| `--radius` | 0.5rem | 0, 1rem, or pill - pick a product feel |
| `--font-sans` | Inter default | deliberate display + body pairing |

Rules:
- Never edit `components/ui/*` - wrap components.
- Import from `@/components/ui/*`, never `@shadcn/ui`.
- Forms: React Hook Form + Zod + `Field`/`FieldGroup`.
- Variants via `cva`, merge via `cn()`.
- Dialog/Sheet: always include Title (sr-only if hidden).

## 10-second slop grep

Before shipping UI code, search for:

```
@tailwind | bg-opacity-| bg-gradient-to | bg-blue-500 | bg-indigo-
space-x-|space-y- | @shadcn/ui | outline-none | transition-all
"use client" (count - sprawl = server-first violated)
middleware.ts on a Next 16 greenfield (should be proxy.ts)
tailwind.config.js without @config (v3 leftover)
from-indigo-|from-violet-|bg-gradient-to-|bg-linear-to-|border-l-4
```

Also: `--primary`, `--radius`, `--font-sans` differ from stock shadcn defaults.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
