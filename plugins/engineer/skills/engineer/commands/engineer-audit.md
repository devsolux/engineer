---
description: Audit code or UI against engineer rubrics — report with severity, no edits.
---

# /engineer-audit

Load engineer `SKILL.md`. Mode: **audit only — no file edits**.

Target: user's path, feature, or "full stack" follows this invocation.

## Output format (mandatory)

Use SKILL.md audit template:

```markdown
## engineer audit: [target]
**Modules**: ...
**Score**: ...

### Critical
- [file:line] (observed|inferred) issue → fix

### Warning
- ...

### Enforcement gaps
- ...

### Passed
- ...
```

## Route by target

| Target | Modules |
|---|---|
| UI / dashboard | design-system, design-accessibility, design-patterns |
| Performance | frontend-performance, frontend-streaming |
| Backend / API | backend-api, backend-auth, backend-database |
| Security | backend-security, backend-auth (rubric score only); to hunt and prove vulnerabilities hand off to `/engineer-security-audit` |
| Enforcement | enforcement.md + maturity L0–L4 |
| Full stack | Score each touched domain |

## Rules

- Quote specific issues with fixes — **no praise padding**
- Recommend scripts/CI for checklist-only gaps
- If Critical > 0, suggest `/engineer-fix` after report
- A request to find or prove vulnerabilities (not score a rubric) routes to `/engineer-security-audit`
