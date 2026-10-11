# Architecture: Turbo monorepo

**Last verified**: 2026-07-14 · **Review cadence**: 6 months

Deep dive for Turborepo workspaces. Single-app layout: `architecture.md`.
Package manager default for this skill: **pnpm** (see workspace `packageManager` field).

## Contents
- [When to monorepo](#when-to-monorepo)
- [Standard layout](#standard-layout)
- [pnpm workspace + catalog](#pnpm-workspace-catalog)
- [turbo.json](#turbojson)
- [Package boundaries](#package-boundaries)
- [Shared UI (shadcn in monorepo)](#shared-ui-shadcn-in-monorepo)
- [Supabase in monorepo](#supabase-in-monorepo)
- [Scripts (root package.json)](#scripts-root-packagejson)
- [Generators](#generators)
- [CI](#ci)
- [Enforcement in monorepo](#enforcement-in-monorepo)
- [Anti-patterns](#anti-patterns)
- [Composition](#composition)

## When to monorepo

| Signal | Action |
|---|---|
| One Next.js app | Stay single repo - see `architecture.md` |
| Web + Expo + shared UI | Monorepo with `packages/ui`, `apps/web`, `apps/mobile` |
| Shared TS types + API client | `packages/shared` or `packages/database` |
| Multiple deployable services | `apps/*` per service + shared libs |

Don't monorepo for organizational preference alone - tooling cost is real.

## Standard layout

```
.
├── apps/
│ ├── web/ # Next.js (primary)
│ └── mobile/ # Expo (optional; out of core for pure web)
├── packages/
│ ├── ui/ # shadcn + shared components
│ ├── database/ # Supabase types, Zod schemas
│ ├── config-eslint/ # shared ESLint config
│ └── config-typescript/ # base tsconfig
├── turbo.json
├── package.json # workspaces + packageManager
├── pnpm-workspace.yaml
└── pnpm-lock.yaml
```

## pnpm workspace + catalog

```yaml
# pnpm-workspace.yaml
packages:
 - "apps/*"
 - "packages/*"
```

**Catalog** (pnpm 9+): pin shared dependency versions once to kill version drift:

```yaml
# pnpm-workspace.yaml (catalog section - syntax per pnpm version)
catalog:
 react: ^19.0.0
 zod: ^3.24.0
 typescript: ~5.7.0
```

```json
// apps/web/package.json
{
 "dependencies": {
 "react": "catalog:",
 "zod": "catalog:"
 }
}
```

Rules:
- One Zod major across the monorepo (`typescript.md`)
- `packageManager` field in root `package.json` for Corepack
- Prefer `pnpm install --frozen-lockfile` in CI
- Avoid `npm install` inside a pnpm workspace (lockfile fights)

## turbo.json

```json
{
 "$schema": "https://turbo.build/schema.json",
 "tasks": {
 "build": {
 "dependsOn": ["^build"],
 "outputs": [".next/**", "!.next/cache/**", "dist/**"]
 },
 "lint": { "dependsOn": ["^lint"] },
 "typecheck": { "dependsOn": ["^typecheck"] },
 "dev": { "cache": false, "persistent": true },
 "test": { "dependsOn": ["^build"] }
 }
}
```

Rules:
- `^build` - dependencies build before dependents
- Cache `outputs` correctly or Turbo replays stale artifacts
- `dev` is never cached
- **Remote cache** (Vercel Remote Cache / Turbo team): enable for CI speed; never cache secrets in task env accidentally - pass env via `globalPassThroughEnv` / task `env` carefully

## Package boundaries

| Package | Contains | Must NOT contain |
|---|---|---|
| `packages/ui` | Presentational components, tokens | Supabase client, secrets, Server Actions |
| `packages/database` | Generated types, shared Zod | React components |
| `apps/web` | Routes, Server Actions, DAL | Duplicated UI primitives |

Import direction: `apps → packages`, never `packages → apps`.
Optional: `eslint-plugin-boundaries` or tsconfig path discipline to fail reverse imports in CI.

## Shared UI (shadcn in monorepo)

Install shadcn into `packages/ui`:

```bash
cd packages/ui
npm install --save-dev --save-exact shadcn@4.13.0
npm exec --offline -- shadcn init
```

Apps import:

```typescript
import { Button } from "@repo/ui/button";
```

Tailwind: content paths must include `packages/ui`:

```css
/* apps/web/app/globals.css - scan shared package */
@source "../../../packages/ui/src/**/*.{ts,tsx}";
```

## Supabase in monorepo

Single source of truth:

```
supabase/ # repo root OR apps/web/supabase
 migrations/
 tests/
packages/database/
 src/types/database.ts # supabase gen types
 src/schemas/ # shared Zod
```

Generate types from root script:

```json
"db:types": "supabase gen types typescript --linked > packages/database/src/types/database.ts"
```

Only `apps/web` runs Server Actions - don't import server-only code into `packages/ui`.

## Scripts (root package.json)

```json
{
 "scripts": {
 "dev": "turbo dev",
 "build": "turbo build",
 "lint": "turbo lint -- --max-warnings=0",
 "typecheck": "turbo typecheck",
 "test": "turbo test",
 "engineer:scan": "bash scripts/engineer-scan.sh --strict"
 }
}
```

Run `engineer-scan` from root with paths covering all apps/packages.

## Generators

If project ships Turbo generators:

```bash
yarn turbo gen component
yarn turbo gen screen
```

Match existing generator patterns - don't hand-roll folder structure.

## CI

```yaml
- run: pnpm install --frozen-lockfile
- run: pnpm turbo lint typecheck test build --filter=web...
```

| Practice | Detail |
|---|---|
| Affected filters | `--filter=...[origin/main]` or package-scoped `web...` on PRs |
| Remote cache | Hit rate matters; warm with main builds |
| Node | 20+ (COMPAT.md) |
| Scan | `bash scripts/engineer-scan.sh --strict` from root |

## Enforcement in monorepo

| Gate | Scope |
|---|---|
| engineer-scan | All `apps/**` and `packages/**` ts/tsx |
| check-rls-migration | Root `supabase/migrations` |
| pgTAP | Root `supabase/tests` |
| ESLint shared | `packages/config-eslint` or root flat config |
| CODEOWNERS | Per-package paths |

## Anti-patterns

| Don't | Do |
|---|---|
| Circular deps between packages | Enforce one-way imports |
| Server Actions in `packages/ui` | Keep mutations in `apps/web` |
| Duplicate tsconfig/eslint | Shared config packages |
| Per-app Supabase migrations | Single migration source |
| Turbo cache wrong outputs | Verify `.next` and `dist` globs |
| Monorepo for one app | `architecture.md` single-app layout |
| Three Zod versions via nested deps | pnpm catalog + one major |
| Mixing npm and pnpm in same tree | One package manager |

## Composition

| Module | When |
|---|---|
| `architecture.md` | Single-app baseline |
| `storybook-dx.md` | Storybook in `packages/ui` |
| `enforcement.md` | CI across workspace |
| `backend-database.md` | Shared types package |
| `typescript.md` | Zod major policy |

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
