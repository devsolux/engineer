# Refactoring research (code + agent skills)

**Date**: 2026-07-13  
**Scope**: Web + GitHub consensus applied to (1) application code on the engineer stack and (2) the engineer skill package itself.  
**Primary sources**: Martin Fowler *Refactoring* 2e / refactoring.com; Anthropic Agent Skills overview + best practices; mgechev/skills-best-practices; arxiv Agent Skills architecture (progressive disclosure); wshobson/agents skill architecture; LLM-assisted refactoring studies (2025).

---

## 1. What refactoring is (and is not)

**Definition (Fowler)**: a disciplined technique for restructuring an existing body of work, **altering internal structure without changing external behavior**.

| Is | Is not |
|---|---|
| Small, behavior-preserving steps | Big-bang rewrite under a feature flag of hope |
| Improves design, readability, changeability | "While we're here" feature additions |
| Safe when tests / evals stay green | Cleanup that ships untested |
| Continuous (boy scout / prepare-to-change) | Only a scheduled "refactoring sprint" |

**Why it matters more with agents (2025–2026)**: LLMs accelerate *generation* of structure; without refactor discipline, repos and skills accumulate **prompt debt**, **duplicated routers**, and **context bloat**. Fowler notes refactoring is *more* relevant when AI writes code: verification and structure become the human/agent edge.

---

## 2. Why refactor

1. **Design decays under short-term edits** - patches without architecture comprehension.
2. **Make the next change cheap** - refactor *before* feature work when structure fights the change.
3. **Reduce defect cost** - clearer modules, less duplication.
4. **Enable tests / evals** - extract pure cores, thin adapters.
5. **Token efficiency (skills)** - progressive disclosure only works if SKILL.md is a TOC, not an encyclopedia.

---

## 3. When to refactor

| Signal | Action |
|---|---|
| **Rule of three** | Same structure thrice → extract |
| **Prepare to change** | Structure blocks a feature → refactor first (still green) |
| **Boy scout** | Leave touched modules cleaner than found |
| **Smell catalog** | Long file, god module, duplicate routing, feature envy |
| **Three strikes** | After third pain point in same area, prioritize refactor |

**Avoid**: refactoring as procrastination; mixing behavior change with structure change; rewriting skills "because AI".

---

## 4. How (mechanics)

### 4.1 Application code (TS / Next / Supabase / Rust)

Standard catalog (Fowler families), mapped to stack:

| Smell | Prefer | Stack note |
|---|---|---|
| Long component | Extract component / hook | RSC default; client only for state |
| Duplicate validation | Single Zod schema at boundary | Server Action + form share schema |
| Fat Server Action | Extract use-case + repo | `getUser()` stays at edge |
| God service | Split by domain | RLS still on tables |
| Nested callbacks | Early return, Result/AppError | Rust: no unwrap in handlers |
| Magic strings | Tokens / constants | Design tokens, not hex in JSX |
| Shotgun surgery | Move feature to one module | Feature folder over layer-only |

**Safety loop** (every step):

```text
1. Baseline green (typecheck, tests, pgTAP, engineer-scan)
2. One structural step (extract / rename / move)
3. Re-run baseline
4. Commit or checkpoint
5. Repeat
```

**Never**: refactor + feature + dep upgrade in one PR.

### 4.2 Agent skills (Anthropic + community)

Three-level progressive disclosure is non-negotiable:

| Level | Content | Budget |
|---|---|---|
| L1 | `name` + `description` only | Always in system prompt |
| L2 | `SKILL.md` body | Load on trigger; **&lt;500 lines** (Anthropic) |
| L3 | `references/`, `scripts/`, `assets/` | On demand; **one level deep** |

**Skill smells → refactorings**:

| Smell | Refactoring |
|---|---|
| Encyclopedia SKILL.md | Extract Module → `references/*.md` |
| Duplicate routing tables | Single index (MANIFEST) + thin SKILL map |
| Nested refs (`a.md` → `b.md` → `c.md`) | Flatten to one hop from SKILL |
| Vague description | Rewrite WHAT + WHEN + triggers + negative triggers |
| Scripts inlined as prose | Move to `scripts/` CLI |
| No evals | Add `evals/evals.json` regression prompts |
| Research in hot path | Keep `research/` L3; link from module footers only |
| Human README bulk-loaded | Agent paths use MANIFEST; humans use `docs/` |

**Degrees of freedom** (Anthropic):

- High: heuristics (code review)
- Medium: templates (audit report)
- Low: scripts (scan, migration gate)

---

## 5. What to refactor *to* (target architecture)

### Application (engineer product code)

```text
UI (RSC) → Server Actions / Route Handlers (Zod + getUser)
         → domain use-cases
         → data access (RLS-backed)
Rust hot paths isolated behind clear API contracts
```

### Skill package (engineer itself)

```text
SKILL.md          # L2 router: principles, verbs, short routes, gates
references/       # L3 modules + MANIFEST (full catalog)
commands/         # Cursor slash = thin wrappers over verbs
scripts/          # Deterministic enforcement
evals/            # Discovery + logic regression
research/         # Corpora, never session bulk-load
docs/             # Humans only
```

**Target properties**:

1. SKILL.md &lt; ~200 lines when possible (router, not catalog)
2. One routing source of truth: MANIFEST owns full map; SKILL owns high-frequency subset + link
3. Every multi-step verb has: intent → modules → output shape → gates
4. Evals cover discovery (trigger / no-trigger) and core pipelines

---

## 6. Why this target (for engineer)

| Pressure | Response |
|---|---|
| 40+ reference modules | MANIFEST + progressive load |
| Context window is shared | Thin L2; refuse bulk-load |
| Multi-host (Cursor, Claude, Codex) | Portable SKILL + optional commands |
| Enforcement must be deterministic | Prefer scripts over regenerated prose |
| Self-host skill-authoring module | Dogfood: skill-authoring.md rules apply to self |

---

## 7. Anti-patterns (research consensus)

- Rewrite without green baseline
- "Improve design" that changes APIs without migration
- Duplicating full module lists in SKILL + MANIFEST without role split
- Nested reference chains
- Description as marketing, not router
- Time-bomb rules ("before Aug 2025")
- Shipping skill changes without eval prompts

---

## 8. Sources (selected)

- https://refactoring.com / Fowler *Refactoring* 2e
- https://martinfowler.com/tags/refactoring.html
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- https://github.com/mgechev/skills-best-practices
- https://github.com/wshobson/agents/blob/main/docs/agent-skills.md
- arXiv: Agent Skills architecture & progressive disclosure (2026)
- arXiv: Refactoring with LLMs + Fowler catalog (2025)

**Operational module**: `references/refactoring.md`
