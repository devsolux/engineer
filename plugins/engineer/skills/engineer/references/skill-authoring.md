# Skill authoring: build agent skills that scale

**Last verified**: 2026-08-19 · **Review cadence**: 6 months

Meta-module for creating and optimizing Cursor/Claude Agent Skills.
Full research: `research/agent-skills-research.md`. Prompting: `ai-agents.md`.
Promotion first: `capability-promotion.md` — authoring is not proof a new skill is the owner.

## Contents
- [Three-level loading](#three-level-loading-mandatory)
- [Description](#description-highest-leverage-field)
- [SKILL.md structure](#skillmd-structure-template)
- [Progressive disclosure](#progressive-disclosure-patterns)
- [Anti-patterns](#anti-patterns)
- [Checklist](#skill-creation-checklist)

## Three-level loading (mandatory)

Aligned with industry Agent Skills progressive disclosure (Anthropic-class L1/L2/L3):

| Level | What | Token cost |
|---|---|---|
| **L1** | YAML `name` + `description` only | ~100 tokens/skill - always in system prompt |
| **L2** | `SKILL.md` body | Loads when skill triggers - keep **under 500 lines** |
| **L3** | `references/`, `scripts/`, `templates/` | On demand only when task needs them |

**Rule**: description is the **router**, not marketing copy. Body is the **workflow**.
Details live in references - never duplicate both in SKILL.md.

**Anti-pattern**: hosts that inject full skill bodies at startup defeat L1. Keep frontmatter tight so routing still works when only metadata is preloaded.

## Description (highest leverage field)

Write third person. Include **WHAT + WHEN + trigger terms**.

```yaml
# Weak - never triggers
description: Helps with fullstack development.

# Strong - routes correctly
description: >-
 Full-stack OS for Next.js and Supabase. Use when the user says engineer,
 engineer plan, engineer audit, or asks for RLS migrations, Stripe webhooks,
 or Vercel deploy on this stack.
```

Include: verb names, stack terms, file types, scenario phrases users actually say.

Measured routing fact (local live evals, 2026-07-16): implicit description-routing is
nondeterministic run-to-run (pass@2), and correct behavior can occur from L1 metadata alone without
a body load - "routing fired" ≠ "body loaded". Invoke any REQUIRED step explicitly (`/name` or the
Skill tool); routing-critical skills ship a live-activation smoke bank with a baseline arm.

## SKILL.md structure (template)

```markdown
---
name: my-skill
description: [third-person router with triggers]
---

# my-skill

One-line purpose.

## Operating principles (5-10 max, binding)
## Verbs or modes (if applicable)
## Routing map (request → reference file)
## End-to-end flows (multi-module pipelines)
## Output format template (for audit/report skills)
## Scripts (how to run, not full source)
## Hard gates

Link to references/MANIFEST.md for full index - do NOT duplicate full module list.
```

## Progressive disclosure patterns

| Pattern | Use when |
|---|---|
| **Router + leaf modules** | Large domain (engineer `frontend.md` → `frontend-performance.md`) |
| **MANIFEST.md** | 20+ reference files - index lives outside SKILL.md |
| **Workflow + checklist** | Repeatable multi-step tasks |
| **Template output** | Audit/review skills need consistent format |
| **Scripts over generated code** | Fragile grep, validation, migrations |
| **Evals** | `evals/evals.json` - regression test prompts |

Keep references **one level deep** from SKILL.md (`references/foo.md`, not `references/a/b/foo.md`).

Open standard ([agentskills.io](https://agentskills.io/specification), 2026-08): required `name` +
`description` (WHAT + WHEN, ≤1024 chars, third person); optional `license`, `compatibility`,
`metadata`; experimental `allowed-tools` (skip unless a host enforces it). Validate with
`skills-ref validate` when that CLI is already installed; do not add a floating package runner.

Plugin packaging (verified 2026-07-16, version-sensitive): `.claude-plugin/plugin.json` +
`marketplace.json`; `@skills-dir` loads skills in place; `defaultEnabled` needs Claude Code ≥2.1.154;
only project-scope installs sit behind the trust gate - personal scope has none; bundled MCP tools
are named `mcp__plugin_<plugin>_<server>__<tool>`.

## Degrees of freedom

| Freedom | When | Example |
|---|---|---|
| High (prose) | Multiple valid approaches | Code review guidelines |
| Medium (templates) | Preferred pattern | Audit report format |
| Low (scripts) | Must be consistent | `engineer-scan.sh`, migration gate |

## Anti-patterns

| Don't | Do |
|---|---|
| Encyclopedia in SKILL.md | Router + references |
| Research in SKILL index | Load via module footers |
| Duplicate routing + full index | Routing map OR manifest, not both |
| Vague description | Trigger verbs and stack terms |
| `I can help you…` in description | Third person |
| Windows paths `scripts\foo.sh` | Forward slashes always |
| Time-sensitive "before Aug 2025" | `Last verified` dates on modules |
| 50+ skills all broad | Narrow skills; compose explicitly |
| No evals | 10+ prompts with assertions |
| Bulk-load all references | Load 1 router + 2-4 leaf modules per task |

## engineer as reference implementation

| Pattern | Where |
|---|---|
| Thin SKILL.md (routers, flows, gates) | `SKILL.md` (keep under 500 lines; the router is not an encyclopedia) |
| Slash commands (Cursor) | `commands/*.md` → `~/.cursor/commands/` |
| Workflow pipelines | `references/workflows.md` |
| Full index offloaded | `references/MANIFEST.md` (canonical catalog) |
| Domain routers | `frontend.md`, `backend-supabase.md` |
| Structure-only changes | `references/refactoring.md` + `engineer refactor` |
| Executable enforcement | `scripts/engineer-scan.sh` |
| CI templates | `templates/github/` |
| Eval suite | `evals/evals.json` |
| Slash commands | `commands/*.md` + `scripts/install-commands.sh` |
| Workflows + loops | `references/workflows.md` |
| Gap audit maintenance | `research/gap-audit.md` |

## Skill creation checklist

- [ ] Description: third person, triggers, WHAT + WHEN, &lt;1024 chars
- [ ] SKILL.md body &lt;500 lines
- [ ] Progressive disclosure: references/ for depth
- [ ] One-level-deep file links
- [ ] Scripts documented with run commands (not pasted source)
- [ ] Evals with assertions for core paths
- [ ] `Last verified` on reference modules
- [ ] No duplicate indexes in SKILL.md
- [ ] Composition table if skill delegates to other skills

## Composition

| Resource | When |
|---|---|
| `ai-agents.md` | Prompting agents to use skills |
| Cursor `create-skill` skill | Cursor-specific authoring |
| Anthropic skill best practices | Platform docs (linked in research) |
| `capability-promotion.md` | Decide whether the durable owner should be a skill at all |
