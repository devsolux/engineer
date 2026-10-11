---
description: Prompt and agent workflow help — four-part specs for Cursor, Claude, Codex.
---

# /engineer-agent

Load engineer `SKILL.md` + `references/ai-agents.md`.

User's agent/prompt question follows this invocation.

## Default response shape

Provide a **four-part spec** they can paste:

```markdown
## Goal
## Scope (touch / do NOT touch)
## Context (@files, modules)
## Acceptance (+ verify commands)
```

## Tool hints

| Tool | Tip |
|---|---|
| Cursor | @files, Agent mode, invoke engineer by name |
| Claude Code | Short prompts, skills in CLAUDE.md, gstack /autoplan |
| Codex | AGENTS.md, explicit verify in acceptance |

## Skill optimization

If user asks about building skills → `references/skill-authoring.md`

## Compose

Stack engineer + gstack + unmachined explicitly in spec when relevant.
