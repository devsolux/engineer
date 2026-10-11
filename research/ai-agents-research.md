# AI agents & prompting research corpus (2026)

**Date**: 2026-07-12 · **Feeds**: `ai-agents.md`

## Executive summary

2026 coding agents (Claude Code, Cursor, Codex, Windsurf, Devin) share the same
success pattern:

1. **Structured specs** beat conversational prompts — goal, scope, context, acceptance
2. **Persistent context files** (`AGENTS.md`, `CLAUDE.md`, skills) — prompts stay short
3. **Verification loops** — agent runs tests/lint before claiming done
4. **Scope boundaries** — explicit "do NOT touch" prevents helpful refactors
5. **Subagents for noise** — exploration/review in separate context; main thread for implementation
6. **Tool-agnostic spec body** — portable across Cursor, Claude Code, Codex
7. **Skills as routers** — progressive disclosure (engineer model) saves tokens
8. **Human checkpoints** — auth, payments, migrations, prod deploys

---

## 1. Agent categories (2026 landscape)

**Sources**: SurePrompts 2026 agent guide, KeepMyPrompts tool comparison, Medium practitioner reports

| Category | Examples | Interaction model |
|---|---|---|
| Terminal-native | Claude Code, Aider | CLI, file-system native, shell access |
| IDE-native | Cursor, Windsurf, Continue | Editor-integrated, @ context, inline |
| Cloud autonomous | Devin, Cursor background | Long-running, needs strong spec + review |
| Scaffold generators | v0, Bolt.new | UI/code seed — must merge into real stack |
| Review/specialist | Bugbot, security agents | Read-only audit, checklist output |

**Segmentation insight**: choose by **workflow**, not benchmark scores. Terminal agents excel at multi-file coherence; IDE agents excel at tight edit loops.

---

## 2. The six transferable prompting skills

**Source**: SurePrompts Complete Guide 2026

1. **Spec-writing** — four-part structure (goal, scope, context, acceptance)
2. **Scope control** — explicit inclusions and exclusions
3. **Context curation** — right files, not all files
4. **Acceptance criteria** — verifiable, testable done conditions
5. **Tool constraint** — which commands agent may run
6. **Critical review** — human or subagent audit before merge

These transfer across Claude Code, Cursor, Codex, Devin, Replit Agent.

---

## 3. Context architecture

**Sources**: alexop.dev Claude customization guide, Cursor create-skill docs, engineer skill design

### Hierarchy (load order)

```
AGENTS.md / CLAUDE.md     → always-on project truth (short)
.cursor/rules             → IDE-specific always-on rules
Skills (SKILL.md)         → triggered workflows
references/               → progressive disclosure modules
User prompt               → this-task spec only
```

### CLAUDE.md vs Skills vs Subagents vs Rules

| Mechanism | Purpose | When |
|---|---|---|
| CLAUDE.md / AGENTS.md | Always-loaded conventions | Stack, safety, skill pointers |
| Cursor Rules | Always-applied patterns | Framework conventions |
| Skills | Router + deep modules | `engineer`, `unmachined`, gstack |
| Slash commands | Explicit one-shot workflows | `/autoplan`, `/ship` |
| Subagents | Separate context window | Explore, review, security scan |
| MCP tools | External systems | Docs, Stripe, Supabase |

**Key insight**: subagents don't inherit full system prompt — shape them deliberately with tight tools and crisp descriptions.

### Progressive disclosure (engineer pattern)

- Router SKILL.md under 500 lines
- Deep knowledge in `references/*.md` loaded on demand
- Research corpora in `research/` for provenance, not hot path

Benefits: lower token burn, fresher context, easier maintenance.

---

## 4. Tool-specific prompting

**Source**: KeepMyPrompts 2026 cross-tool guide

### Claude Code

- Persistent rules in `CLAUDE.md` → **short imperative prompts**
- Don't restate project rules in each message
- Single-purpose prompts; chain sequentially for multi-phase work
- gstack integration via `AGENTS.md` spawn hints

### Cursor

- `@file` / `@folder` / `@docs` for surgical context
- Agent vs Ask vs Plan modes — match mode to task phase
- Skills discovered via description field in frontmatter
- Composer/Agent for multi-file; inline for single-function

### Windsurf / Cascade

- Time/token caps on cascade runs
- Similar spec format; tool-specific headers for cascade limits

### Codex / OpenAI coding agents

- `AGENTS.md` standard emerging (OpenAI, community)
- Same four-part spec
- Explicit verify steps critical — tendency to over-edit without scope

### Portable prompt library pattern

```
[tool header — optional, 2-3 lines]
[tool-agnostic body — goal, scope, context, acceptance, verify]
```

Score prompt variants; reject tool-specific tweaks that hurt portability.

---

## 5. Subagents and parallel work

**Sources**: Builder.io Claude subagents guide, Anthropic Task tool docs

### When to delegate

| Delegate | Keep in main |
|---|---|
| Repo exploration / file mapping | Implementing approved plan |
| Security read-only review | Interactive UI taste decisions |
| Test failure triage across many files | Single-file bug fix |
| Research corpus synthesis | Clarifying product requirements |

### Configuration levers

- `description` — routing signal; action verbs win
- `tools` — minimum viable (Read/Grep for reviewers)
- `model` — cheaper/faster for exploration
- `background: true` — concurrent non-blocking work
- `isolation: worktree` — parallel edits without collision
- `maxTurns` — cap runaway agents

### Reviewer subagent pattern

Read-only tools + checklist + severity format — same as `engineer audit`.

---

## 6. Verification and closed-loop agents

**Sources**: SurePrompts, engineer enforcement.md, practitioner workflows

Agents without verify steps ship broken code. Minimum closed loop:

```
implement → typecheck → lint → test → engineer-scan → report results
```

Include verify commands in **acceptance section**, not as afterthought.

| Domain | Verify |
|---|---|
| TypeScript | `tsc --noEmit` |
| Style/a11y | `eslint --max-warnings=0` |
| Policy | `engineer-scan --strict` |
| Logic | `vitest run path` |
| E2E | `playwright test smoke` |
| RLS | `supabase test db` |

Agent should **paste command output** or explicitly state what was run.

---

## 7. Context rot and session hygiene

**Sources**: practitioner reports, token economics

### Symptoms

- Re-asks resolved questions
- Forgets "do not touch" constraints
- Scope creep / drive-by refactors return
- Contradicts earlier decisions in same thread

### Fixes

1. Start fresh thread with **state summary** + spec
2. One feature per session when possible
3. Move standing rules to CLAUDE.md instead of re-prompting
4. Use subagents so exploration doesn't bloat main context
5. Checkpoint: "Stop. Summarize progress. Wait for approval."

### When to continue vs restart

| Continue | Restart |
|---|---|
| Same feature, agent remembers constraints | New feature unrelated to thread |
| Mid-fix with good context | Context >50% exploration noise |
| Awaiting your answer on one decision | Agent clearly confused |

---

## 8. Scope creep and the "helpful refactor" problem

**Sources**: Kevin Gabeci Medium 2026, CLAUDE.md community rules

Agents optimize for "helpful" — will refactor adjacent code, add unrequested
features, or expand scope unless constrained.

**Mandatory prompt lines**:
- "Minimal diff — only change what's required"
- "Do NOT refactor unrelated code"
- "Do NOT add features not in acceptance criteria"
- "Match existing repo conventions"

`CLAUDE.md` rule example: "When user asks for simple change, make ONLY that change."

Human review catches the rest.

---

## 9. Planning pipelines

**Sources**: gstack autoplan, engineer verbs, SurePrompts

High-stakes sequence:
```
1. engineer plan / gstack autoplan  → architecture + file plan
2. Human approve plan
3. engineer implement with acceptance criteria
4. engineer audit or gstack /review
5. engineer enforce verify + gstack /ship
```

Plan mode prevents expensive wrong-direction implementation.

---

## 10. Skill design for agents (engineer as exemplar)

**Sources**: Cursor create-skill, engineer architecture

Effective skill properties:
- **Third-person description** — agent discovers when to invoke
- **Router pattern** — SKILL.md routes to references/
- **Verbs** — `engineer audit`, `engineer plan` disambiguate behavior
- **Composition table** — when to delegate to unmachined, gstack, vercel skills
- **Hard gates** — non-negotiables agent must not skip
- **Evals** — `evals/evals.json` for regression testing skill behavior

Install:
```bash
ln -s /path/to/engineer ~/.cursor/skills/engineer
ln -s /path/to/engineer ~/.claude/skills/engineer
```

---

## 11. Security and trust boundaries

Agents must not autonomously:
- Apply prod migrations without approval
- Commit secrets or disable RLS
- Force push / hard reset
- Skip hooks (`--no-verify`) unless user explicitly requests
- Expose service role keys in client code

Use `engineer audit` + gstack `/cso` for auth/payment surfaces.

Treat agent output as **untrusted until verified** — same as junior dev PR.

---

## 12. Module map

| Topic | Reference |
|---|---|
| Daily agent workflows | `ai-agents.md` |
| Project rules spawn | root `AGENTS.md` |
| Fullstack build rules | `SKILL.md` (engineer router) |
| Verify automation | `enforcement.md` |
| Plan quality | `coding-principles.md`, `system-architecture.md` |

---

## Canonical sources

- https://sureprompts.com/blog/the-complete-guide-to-prompting-ai-coding-agents-2026
- https://www.keepmyprompts.com/en/blog/cursor-3-claude-code-windsurf-prompt-strategies-agent-first-ides
- https://alexop.dev/posts/claude-code-customization-guide-claudemd-skills-subagents/
- https://www.builder.io/blog/claude-code-subagents
- https://kgabeci.medium.com/ai-coding-agents-in-2026-claude-code-cursor-and-how-we-actually-use-them-d76d9c397d82
- Cursor create-skill documentation
- Local: `~/AGENTS.md`, gstack skills at `~/.claude/skills/gstack`
