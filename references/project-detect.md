# Project detection

**Last verified**: 2026-08-21 · **Review cadence**: 3 months

**Load**: every engineer session start (before generating code).

| Related | When |
|---|---|
| `stack-rules.md` | After versions detected |
| `architecture.md` | Repo layout |
| `architecture-monorepo.md` | Turbo workspace detected |
| `frontend.md` / `backend-supabase.md` | Routers after stack known |
| `workflows.md` | Outer-loop contract + risk gates (after detect) |
| `ai-boundary.md` / `ai-security.md` | AI features or tools/MCP detected |
| `oss-maintainer.md` | Confirmed public/OSS repository or explicit OSS task |
| Harness checklist | Multi-host agent work - see below |

Read before generating code. The agent's defaults lag real projects; detect
first, then apply rules.

Plan state is part of detection: check `.engineer/plan.json` and `.engineer/plans/*.json` for
non-done plans before creating one — resume, split off a named stream, or explicitly supersede;
never silently duplicate a stream (lifecycle: SKILL.md Plan → Validate → Execute).

## Detection checklist

1. **`package.json` dependencies**
 - `next` - 16.x (greenfield, Cache Components, `proxy.ts`) vs 15 (`middleware.ts`) vs 14
 - `react` / `react-dom` - 19 vs 18
 - `tailwindcss` - 4.x vs 3.x
 - `@supabase/supabase-js`, `@supabase/ssr`
 - `zod`, `react-hook-form`, `@hookform/resolvers`
 - `@tanstack/react-query` (if present, follow its patterns)

2. **Tailwind version signal**
 - v4: `@import "tailwindcss"` in CSS, `@theme { }` block, no JS config
 - v3: `tailwind.config.js/ts`, `@tailwind base/components/utilities`

3. **Next.js signal**
 - `cacheComponents: true` in `next.config.ts` → Cache Components / `use cache` rules apply (greenfield 16.x default)
 - Root interceptor: `proxy.ts` (16+) vs `middleware.ts` (15)
 - App Router: `app/` directory with `layout.tsx`
 - Pages Router: `pages/` - do not mix patterns in one route

4. **shadcn signal**
 - `components.json` present
 - Run the locked local CLI with `npm exec --offline -- shadcn info --json` when generating components
 - Check `base`: radix vs base-ui, `isRSC`, icon library, aliases
 - `DESIGN.md` / `design.md` at repo root is a locked visual system: preserve tokens, type, and tone; load `design-taste.md` only to enforce it, not to replace it
 - No DESIGN.md on a new UI/landing task → load `design-taste.md` before pixels

5. **Supabase signal**
 - Client helpers: `lib/supabase/server.ts`, `client.ts`, plus `proxy.ts` or `middleware.ts` (`updateSession`)
 - Root interceptor: Next 16 `proxy.ts` (or detected Next 15 `middleware.ts`); session refresh must run here
 - `supabase/migrations/` or linked remote project
 - Env vars: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`

6. **Rust signal**
 - `Cargo.toml` / workspace `Cargo.toml`
 - Axum, tokio, sqlx in dependencies
 - `src/main.rs`, `crates/*` layout

7. **Python signal**
 - `pyproject.toml`, `uv.lock`, `.python-version`
 - FastAPI / uvicorn / pydantic / sqlalchemy in dependencies
 - Layout: `services/**/*.py`, `src/*/main.py`, `packages/py-*`
 - Load `python.md` + `ai-boundary.md` for services, workers, AI - not notebook UIs

8. **AI / agent harness signal**
 - LLM SDKs (`openai`, `@ai-sdk/*`, anthropic, litellm) → `ai-boundary.md` + `ai-evals.md`
 - MCP config / skill installs → `ai-security.md` (always-ask before new servers)
 - Multi-host coding agents → harness checklist (tools, perms, context, verify, traces)
 - Deeper harness design: local corpus `ai-harness-research` (composition.md); do not bulk-load

9. **Conventions signal**
 - Import alias (`@/` vs `~/`)
 - `src/` vs root-level `app/`
 - Existing feature folder pattern (`features/`, `components/`, colocated)

10. **Distribution / OSS signal**
 - Explicit user statement or host API `visibility: PUBLIC` confirms OSS/public mode
 - `LICENSE`, community files and a GitHub remote are hints only; do not infer visibility or license intent
 - Classify `experimental`, `supported`, `critical`, or `deprecated`
 - Automatically load `oss-maintainer.md` for repository setup, implementation, contribution, workflow, security, release and ship tasks
 - Run `python3 scripts/audit-oss-repo.py . --visibility public --profile <profile> --json`; for authorized repository changes follow with `python3 scripts/apply-oss-baseline.py . --visibility public --apply --output <receipt>`, validate that receipt against the target, then re-audit. Unknown visibility fails closed and confirmed private repositories are excluded
 - Query effective host settings before claims; ask before settings, access, vulnerability-reporting, release or package mutations

11. **Workspace/portfolio truth** (`portfolio-context.md`)
 - Workspace registry and global agent policy file present → portfolio member
 - Control-plane repo present → read `config/workspace-policy.json` (repo→venture via `repo_ventures`) and the `data/workspace-health.json` snapshot; never rescan the filesystem
 - Venture not in the mapping → "unknown — ask"; venture on hold / automation off / workspace unhealthy → flag before shipping
 - Cross-repo contract change → load `portfolio-context.md` impact checklist

## Profile: local-trust ops dashboard (example: a control-plane command center)

When the app is a **single local command center** (filesystem + scripts, not multi-tenant SaaS):

```
Stack: Next 15.x (or as pinned), React 19, Tailwind 4, Supabase no, shadcn yes (Base UI),
 Zod thin or none, Rust no
Patterns: App Router, src/, alias @/
Constraints: single app path, loopback-first host, optional shared-secret on mutating APIs
Python plane: automation scripts/crons OUTSIDE FastAPI peer defaults
```

- **Do not** force Supabase, Stripe, or `python.md` FastAPI service scaffolds.
- **Do** keep Tailwind 4 + shadcn; match `components.json` base (radix vs base-ui).
- **Do** treat loopback + opt-in secret as the security model, not cookie SSR multi-user auth.
- Reference project research if present (e.g. a control-plane repo's `research/dashboard-stack-profile-*.md`).

## Version conflict rule

If the project pins older versions, follow the project and flag the pin.
Never mix Tailwind v3 and v4 syntax in one codebase.

## Greenfield default rule

Detection distinguishes *absence* from *opt-out*. In a new or empty Next.js
project (or when engineer is creating one), missing Tailwind/shadcn signals mean
**scaffold them in** — Tailwind v4 + shadcn/ui is the binding greenfield
default (`stack-rules.md` → Greenfield default stack). In an established
codebase, the same absence is project truth: follow the existing styling
system and flag the divergence; never retrofit uninvited.

## Output template

After detection, state:

```
Stack: Next {v}, React {v}, Tailwind {v}, Supabase {y/n}, shadcn {y/n}, Rust {y/n}, Python {y/n}
Rust: {Axum/none}, workspace {y/n}
Python: {FastAPI/none}, uv {y/n}, services path {path|none}
Patterns: {App Router|Pages}, {src/|root}, alias {path}
Constraints: {cacheComponents|none}, {monorepo|single app}
Distribution: {private|public/OSS|unknown}, OSS profile {experimental|supported|critical|deprecated|n/a}
Portfolio: venture {key|unknown}, workspace {healthy|attention|n/a}
```

Then proceed to the routed module.

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
