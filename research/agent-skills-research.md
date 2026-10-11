# Agent skills research corpus

**Date**: 2026-07-12 · **Sources**: Anthropic skill guide, Claude Platform docs,
Cursor create-skill, agentskills.io open standard, 2026 practitioner guides.

## Executive summary

Agent Skills are **folders with SKILL.md** — portable instructions that load
progressively to save context tokens. The description field is the **router**;
the body is the **workflow**; references/scripts are **on-demand depth**.

engineer implements this pattern: 180-line SKILL.md, 40+ reference modules,
executable scanners, 25+ evals.

## Three-level progressive disclosure

| Level | Content | When loaded | Token budget |
|---|---|---|---|
| L1 Metadata | `name`, `description` in YAML | Startup / skill discovery | ~100 tokens per skill |
| L2 Instructions | SKILL.md body | Skill triggers | &lt;500 lines / ~5k tokens |
| L3 Resources | references/, scripts/, templates/ | Agent reads or executes on need | Unbounded but lazy |

**Key insight** (Anthropic): pre-load only enough for routing decisions. Full
procedural knowledge loads after relevance is established. Scripts run via shell —
output enters context, not source code.

## Description as router

The description is injected into system prompt for **every** skill. It must:

1. Be **third person** ("Processes PDFs…" not "I can help…")
2. State **what** the skill does (capabilities, stack, outputs)
3. State **when** to use it (verbs, file types, user phrases)
4. Include **trigger terms** agents match against user messages

Weak descriptions cause **silent failure** — skill never loads, agent improvises.

Strong pattern: `[Capabilities] + Use when [verbs/scenarios/phrases].`

## SKILL.md body constraints

- **Under 500 lines** (Anthropic + Cursor consensus)
- Essential workflows only — challenge every paragraph's token cost
- Assume agent is smart — don't explain basics
- **No duplicate indexes** — routing map OR manifest, not both listing 40 modules
- **No research corpora in top-level index** — load via module footers
- Forward slashes in all paths
- Consistent terminology (pick "deploy" OR "release", not both)

## Reference file patterns

| Pattern | Purpose |
|---|---|
| Router module | Submodule table + when to load (`frontend.md`) |
| Leaf module | Single domain deep dive (&lt;350 lines ideal) |
| MANIFEST.md | Full index when skill has 20+ modules |
| research/*.md | Provenance corpus — never bulk-load |
| templates/ | Copy-paste CI, ESLint, pgTAP starters |
| scripts/ | Policy grep, validation — run don't read |
| evals/evals.json | Prompt + expected_output + assertions |

Long references (&gt;100 lines): add **table of contents** at top for partial reads.

## Workflow patterns (from Anthropic)

1. **Checklist** — track multi-step progress explicitly
2. **Conditional** — branch on task type (create vs edit)
3. **Template output** — audit reports, specs, commit format
4. **Feedback loop** — run validator script; fix until pass
5. **Examples** — concrete input/output pairs for ambiguous tasks

## Evals (quality gate for skills)

Each eval should have:
- Realistic user prompt
- `expected_output` describing routing and behavior
- `assertions` — verifiable checks (not subjective)
- Optional `files` — fixture paths for integration evals

Cover: core verbs, routing disambiguation, negative cases (wrong module),
composition with other skills.

## Skill portfolio hygiene

- **20–50 enabled skills max** — each description competes for routing
- Narrow skills &gt; one mega-skill (compose explicitly: "engineer + unmachined")
- `disable-model-invocation: true` for manual-only skills (Cursor)
- Re-audit every 6 months or on platform changes
- Gap audit: add module when gap hits **3+ projects** or is **ship-blocking**

## engineer optimizations applied

| Change | Rationale |
|---|---|
| Removed duplicate reference index from SKILL.md | ~1500 token savings per load |
| Added MANIFEST.md | Full index on demand |
| Research corpora demoted to module footers | Prevent 1500+ line accidental loads |
| Description adds verb triggers | Better routing (plan, audit, ship, RLS…) |
| Audit output template in SKILL.md | Consistent `engineer audit` behavior |
| Disambiguation table | "design schema" → backend not design-system |
| skill-authoring.md + this corpus | Meta guidance for skill builders |
| Expanded evals | plan/fix/flow, flags, monorepo, observability |

## References

- [Anthropic: Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [Claude Platform: Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- Cursor create-skill skill (`~/.cursor/skills-cursor/create-skill/SKILL.md`)
- [Agent Skills open format](https://agentskills.io) (portable across tools)
