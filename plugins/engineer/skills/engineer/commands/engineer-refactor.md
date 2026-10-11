---
description: Refactor application code or this skill package — structure only, behavior preserved, verified in atomic steps.
---

# /engineer-refactor

Refactor application code or this skill package. Structure only; preserve behavior.

## When

User says: refactor, clean up structure, extract module, reduce duplication, thin SKILL.md, progressive disclosure, tech debt in structure.

## Do

1. Read `references/project-detect.md` if working in an app repo.
2. Load `references/refactoring.md` (required).
3. Optionally: `coding-principles.md`, `code-quality.md`, domain modules for the touched area.
4. Emit the **refactor plan** template from `refactoring.md` before large edits.
5. Execute in atomic steps; re-verify after each step.
6. For skill package changes: update `evals/evals.json` when routes/verbs change; keep SKILL.md as router.

## Don't

- Mix features into the refactor
- Bulk-load all of `references/` or `research/`
- Rewrite from scratch without baseline green
- Change public APIs without calling it a migration

## Related

- `engineer fix` — audit then repair (may include small refactors)
- `engineer plan` — architecture before code when scope is large
