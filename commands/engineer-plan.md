---
description: Architecture and file plan only — no code until approved. Use for multi-file or schema features.
---

# /engineer-plan

Load engineer `SKILL.md`. Mode: **plan only — no implementation code**.

User's feature request follows this invocation.

## Output (required sections)

Human markdown **and** machine artifact:

```markdown
## Goal
## Architecture (diagram or bullets)
## Files to create / modify
## Data flow
## Migrations / RLS (if any)
## Module references used
## Acceptance criteria
## Risks / open questions
## Plan artifact path
`.engineer/plan.json` — or `.engineer/plans/<slug>.json` for a parallel/multi-session stream
```

Before writing, run the activation-time plan check (SKILL.md Plan → Validate → Execute): resume a
matching active plan, split off a named stream when `plan.json` belongs to other work, or adopt
in-flight work retroactively (`origin: "adopted-mid-session"` + `resume_context`).

Write the plan (schema: `templates/plan-artifact.schema.json`):

| kind | Required extras |
|---|---|
| `feature` | summary, files_touch, verify_commands, risks |
| `schema` | tables, rls_policies, migrations, tests, risks |
| `scan-fix` | findings[] with file, rule_id, proposed_fix, verify_command |
| `ship` | verify_commands, risks |

Validate before execute:

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
bash "$ENGINEER/scripts/validate-plan.sh" .engineer/plan.json   # or the plans/<slug>.json path
bash "$ENGINEER/scripts/validate-plan.sh" --all .             # sweep every plan under .engineer/
```

Optional eng lock: gstack **`plan-eng-review`** after the artifact is written (architecture pressure-test). Ownership: `references/composition.md`.

## Route

| Task type | Modules |
|---|---|
| Schema-heavy | backend-database, backend-multitenant, backend-auth, system-architecture |
| UI feature | frontend, design-patterns, api-data-flows |
| Async / jobs | background-jobs, observability |
| API / Rust | api-data-flows, rust, system-architecture |
| Greenfield | See `/engineer-greenfield` pipeline |

## Rules

- **No code** until user approves ("approved", "LGTM", "build it") and plan validates
- After approval set `status: approved` in plan.json → `/engineer` with same scope
- Always plan before: migrations, auth, payments, >3 files
- Skip full artifact only for one-line typos

## Handoff

```
validate-plan.sh OK + user approves → /engineer <same task>
Optional: gstack plan-eng-review if architecture risk is high
```

