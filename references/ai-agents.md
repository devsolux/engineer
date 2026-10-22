# AI agents: prompting, context, and efficient workflows

**Last verified**: 2026-10-22 · **Review cadence**: 3 months

How to work effectively with Claude Code, Cursor, Codex, and coding agents.
Full research: `research/ai-agents-research.md`
Outer-loop contract + risk gates: **`workflows.md`** (binding).
AI tools/MCP: **`ai-security.md`**. Handoffs: **`composition.md`** (portage).

## Contents
- [Tool landscape](#tool-landscape)
- [The agent spec (use every time)](#the-agent-spec-use-every-time)
- [Context stack](#context-stack)
- [Prompting by tool](#prompting-by-tool)
- [Modes: plan vs build vs audit](#modes-plan-vs-build-vs-audit)
- [Subagents and delegation](#subagents-and-delegation)
- [Verification loops](#verification-loops)
- [Token and context efficiency](#token-and-context-efficiency)
- [engineer + skill composition](#engineer--skill-composition)
- [Skill authoring (meta)](#skill-authoring-meta)
- [Prompt templates](#prompt-templates)
- [Human checkpoints](#human-checkpoints)
- [Anti-patterns](#anti-patterns)

## Tool landscape

| Type | Tools | Best for |
|---|---|---|
| **Terminal-native** | Claude Code, Codex CLI, Aider | Multi-file refactors, backend, shell, CI |
| **IDE-native** | Cursor, Devin Desktop (ex-Windsurf) | Inline edits, frontend iteration, @ file context |
| **Cloud autonomous** | Devin, Cursor Cloud Agents (ex-Background Agents), Codex cloud | Long-running scoped tasks (with review) |
| **App/UI generators** | v0, Bolt | Scaffolding - always integrate into real stack after |

**2026 practical split** (common team pattern):
- **Claude Code** - substantial multi-file features, migrations, refactors
- **Cursor Agent** - UI polish, quick fixes, exploratory debugging
- **Human editor** - one-line fixes, taste calls agents miss

Prompts should be **tool-agnostic in the body**; add a thin tool header only when needed.

## The agent spec (use every time)

Replace conversational nudges with a **four-part spec**:

```markdown
## Goal
[One sentence: what done looks like]

## Scope
- Touch: [files/areas]
- Do NOT touch: [explicit exclusions]
- Match: [repo conventions / engineer modules]

## Context
- Stack: [detect from repo or state Next + Supabase + …]
- Relevant: @path/to/file.ts, references/backend-auth.md
- Prior art: [similar feature in codebase]

## Acceptance
- [ ] [Verifiable check 1 - e.g. getUser() on action]
- [ ] [Verifiable check 2 - e.g. npm run typecheck passes]
- [ ] [Verifiable check 3 - e.g. engineer-scan --strict]
```

Agents need **stop conditions** and **acceptance criteria** - not "make it nice."

## Context stack

Load rules once; don't repeat in every prompt.

| Layer | File | Loaded when | Put what here |
|---|---|---|---|
| Project rules | `AGENTS.md`, `CLAUDE.md` | Every session | Stack, gstack hooks, non-negotiables |
| Cursor rules | `.cursor/rules/*.mdc` | Cursor sessions | TS/React conventions |
| Skills | `SKILL.md` + `references/` | On trigger (`engineer`, `unmachined`) | Workflows, progressive disclosure |
| Prompt | Your message | This task only | Goal, scope, acceptance for *this* run |

**Progressive disclosure** (engineer pattern): thin router in `SKILL.md`; load
`references/*.md` only when the task needs them - saves context window.

Rules:
- Keep `CLAUDE.md` / `AGENTS.md` **short** (under 200 lines) - pointers to skills, not encyclopedias
- Claude Code (2.1.277+) reads `AGENTS.md` only when no `CLAUDE.md` exists; with both, put `@AGENTS.md` in `CLAUDE.md`
- **Don't paste** entire files if `@` reference or skill module exists
- **Project detect first** - agent reads `package.json`, `supabase/`, etc. before generating

## Prompting by tool

### Claude Code

- **Short, imperative** prompts - standing rules live in `CLAUDE.md`
- One purpose per prompt; chain only when needed
- Use **skills** (`engineer`, gstack `/autoplan`) for workflows
- **Subagents** for repo exploration - keeps main thread clean
- Spawn hint: `Load gstack. Run /autoplan` (gstack install adds a `## gstack` section to `CLAUDE.md`)

### Cursor

- Use **`@files` / `@folders`** for precise context - not whole-repo dumps
- **Agent mode** for multi-file; **Ask** for understanding only
- Invoke skills via `/engineer` or by name: `engineer - build signup flow`
- **Plan mode** for architecture before large diffs
- Re-`@` critical files in long sessions

### Codex / OpenAI agents

- Same four-part spec format
- `AGENTS.md` at repo root for persistent instructions (root → cwd chain; 32 KiB default cap)
- Explicit verify commands in acceptance section
- Scope boundaries critical - agents over-refactor without them

## Modes: plan vs build vs audit

| Mode | When | engineer verb |
|---|---|---|
| **Plan** | >3 files, schema change, new feature area | `engineer plan` |
| **Build** | Spec approved, clear acceptance | `engineer <task>` |
| **Audit** | Review only, no edits | `engineer audit` |
| **Fix** | Audit findings → repair | `engineer fix` |

**Always plan before** migrations, auth changes, payment flows, or greenfield modules.

gstack pipeline for high-stakes work:
```
/office-hours → /autoplan → [approve plan] → implement → /review → /ship
```

## Subagents and delegation

Use subagents (Agent tool; `Task` before Claude Code 2.1.63) when work is:
- **Noisy** - lots of search/read before a small output
- **Bounded** - clear deliverable (report, file list, security scan)
- **Parallelizable** - independent research tracks

Stay in main thread when:
- Small, tightly coupled change
- Shared mental model would break after summarization
- You need interactive steering mid-implementation

Subagent config best practices:
- Sharp **description** (action-oriented, not vague)
- **Minimal tools** - read-only for reviewers
- **`background: true`** to stay async even when Claude asks to wait (spawned subagents already start in background)
- **`isolation: worktree`** for parallel edits that might collide (branches from the default branch, not `HEAD`)

Example delegation:
```
Agent: Explore subagent - map all Server Actions missing getUser(); return file list only.
Main thread: fix each file using backend-api.md gates.
```

## Verification loops

Every build prompt must include **how to verify**:

```markdown
## Verify
npm run typecheck
npm run lint:ci
npm run engineer:scan -- --strict
npm run test:unit -- path/to/feature
# Manual: signup flow at /signup in dev
```

Agent should run checks **before** declaring done. You review diff + spot-check.

| Task type | Minimum verify |
|---|---|
| UI feature | typecheck + lint + visual spot-check |
| Server Action | typecheck + auth grep + unit test |
| Migration | RLS check script + types regen |
| Landing page | engineer-scan --design + a11y lint |

## Token and context efficiency

1. **Spec > essay** - 20 lines beats 200 lines of repetition
2. **Don't repeat** what's in CLAUDE.md / engineer SKILL.md
3. **Load references on demand** - "follow backend-auth.md" not paste entire file
4. **Fresh thread** when: context feels confused, unrelated tasks piled up, or >50% window is stale exploration
5. **Summarize state** when continuing: "We added X; remaining: Y; files touched: …"
6. **One feature per session** when possible - reduces scope creep
7. **Batch independent tasks** - parallel subagents, not one mega-prompt

Signs of **context rot**: agent forgets constraints, re-asks answered questions,
reverts prior decisions, or expands scope unprompted → start new thread with spec.

## engineer + skill composition

engineer is a **router skill** - invoke it to load the right reference modules:

```
engineer - build Stripe webhook handler
 → loads backend-webhooks.md, backend-database.md, enforcement.md
 → composes gstack /cso before ship
```

| Skill | Invoke when |
|---|---|
| `engineer` | Any fullstack build/audit on your stack |
| `unmachined` | Copy/UI anti-slop on marketing or product UI |
| vercel `react-best-practices` | React/Next performance pass |
| gstack `/autoplan` | Plan review pipeline before big builds |
| gstack `/cso` | Security before auth/payment webhooks |
| gstack `/qa` | QA running app/API + fix (`/qa-only` = report) |
| gstack `/ship` | Test, push, open PR (needs push approval) |

**Rule**: read and follow skill instructions immediately - don't announce without doing.

Stack multiple skills explicitly when needed:
```
engineer page - B2B landing. After build, unmachined audit on hero copy.
```

## Skill authoring (meta)

When building or optimizing agent skills (including engineer itself):

| Principle | Action |
|---|---|
| Description = router | Third person; WHAT + WHEN + trigger verbs |
| SKILL.md &lt;500 lines | Workflows, routing, gates - not encyclopedia |
| Progressive disclosure | `references/` for depth; `MANIFEST.md` for full index |
| Scripts over paste | Run `scripts/*.sh`; don't dump source into chat |
| Evals | `evals/evals.json` with assertions per core path |
| No duplicate indexes | Routing map in SKILL.md; manifest on demand |

Full guide: `references/skill-authoring.md`
Research: `research/agent-skills-research.md`

## Prompt templates

Copy-paste bodies live in `templates/agentic/prompts/` (load only the one needed):

| Template | File |
|---|---|
| Feature build (goal/scope/context/acceptance) | `templates/agentic/prompts/feature-build.md` |
| Bug fix (repro, causal-site diff, root-cause vs mitigated report) | `templates/agentic/prompts/bug-fix.md` |
| Audit only (rubric score, no edits) | `templates/agentic/prompts/audit-only.md` |
| Plan only (architecture + files, no code until approval) | `templates/agentic/prompts/plan-only.md` |

## Human checkpoints

Require human approval before:
- Schema/RLS migrations applied to prod
- Force push, hard reset, `--no-verify`
- Commit/push (unless explicitly requested)
- Payment/auth webhook deploy
- Deleting files or large renames
- Scope expansion beyond original spec

Review agent diffs like a **junior PR** - agents "helpfully" refactor adjacent code.

## Anti-patterns

- "Make it better" / "clean up" without scope
- No acceptance criteria - agent can't know when to stop
- Pasting 500 lines instead of `@file` reference
- Repeating CLAUDE.md rules in every prompt
- One prompt for five unrelated features
- Skipping verify commands - shipping uncompiled code
- Trusting agent on security/auth without audit module
- Never starting fresh thread when context is polluted
- Arguing with agent in prose instead of updating spec/CLAUDE.md
- Letting agent commit secrets or disable RLS "temporarily"

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
