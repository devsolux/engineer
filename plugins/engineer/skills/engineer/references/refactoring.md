# Refactoring: when, what, how, why

**Last verified**: 2026-07-13 · **Review cadence**: 6 months
**Research**: `research/refactoring-research.md`
**Compose**: `coding-principles.md`, `code-quality.md`, `typescript.md`, `skill-authoring.md`

## Definition

Change **structure** to improve changeability and clarity **without** changing observable behavior (Fowler). For skills: same triggers and outputs, thinner load path.

## Why

- Make the next feature cheap
- Kill duplication and god modules
- Keep tests/evals as the safety net
- For agents: shrink context (progressive disclosure)

## When

| Trigger | Do |
|---|---|
| Rule of three | Extract shared module / schema / component |
| Prepare-to-change | Structure blocks a feature → refactor first |
| Boy scout | Clean only what you touch |
| Smell list | Long file, shotgun surgery, feature envy, fat SKILL.md |
| Three strikes | Same pain thrice → prioritize |

**Do not** refactor for aesthetics alone mid-incident, or mix feature + structure + upgrade.

## How (application code)

### Safety loop

1. Green baseline: `tsc` / lint / tests / `supabase test db` / `engineer-scan --strict` as available
2. One step (extract, rename, move, inline)
3. Green again
4. Commit
5. Repeat

### Common stack moves

| Smell | Move | Refs |
|---|---|---|
| Fat React component | Extract presentational + container; prefer RSC | frontend, design-patterns |
| Duplicate Zod | One schema shared by form + action | typescript, backend-api |
| Fat Server Action | Extract use-case; keep auth at edge | backend-api, backend-auth |
| Color / spacing chaos | Semantic tokens only | design-system |
| Unwrap / panic paths | `AppError` / Result | rust-idioms, rust, backend-api |
| Rust borrow-checker clones, `&String` params, `get_` getters, `bool` params | Pin behavior with tests, then the rust-idioms refactor pass | rust-idioms, rust-review |
| Cross-cutting copy | Shared module, not paste | coding-principles |

### PR hygiene

- Title: `refactor: …` (no behavior change claimed unless tested)
- Diff minimal; no drive-by features
- Note risk surface and how verified

## How (agent skills / this package)

| Smell | Refactoring |
|---|---|
| SKILL.md encyclopedia | Extract to `references/`; keep &lt;500 lines (target &lt;200) |
| Dual full routing tables | MANIFEST = full catalog; SKILL = short routes + link |
| Nested refs | One hop from SKILL.md |
| Vague description | Third person, WHAT + WHEN + triggers + negative triggers |
| Fragile multi-step prose | `scripts/` CLI |
| No regression net | `evals/evals.json` |

### Skill safety loop

1. Discovery check: description triggers only intended prompts
2. Logic walk: agent can follow steps without guessing
3. Edge cases documented
4. Eval prompts updated when routes change

## Output format (`engineer refactor` / audit)

```markdown
## refactor plan: [target]
**Goal**: [structure improvement]
**Behavior preserved**: [APIs / UX / skill outputs]
**Baseline**: [commands + green/red]

### Smells
- [smell] → [refactoring name] → [files]

### Steps (atomic)
1. …
2. …

### Verify
- [ ] typecheck / tests / scan / evals
- [ ] no public API change (or migration noted)
```

## Hard gates

- No behavior change without tests/evals
- One concern per step
- Prefer extract over rewrite
- Skills: do not bulk-load `research/` during normal tasks

## Anti-patterns

- Rewrite "clean architecture" in one PR
- Refactor by generating a new skill copy and abandoning the old
- Deleting gates to make green
- Nested reference chains for "organization"

---

Research corpus: `research/` (index `research/report.md`). Load on demand only.
