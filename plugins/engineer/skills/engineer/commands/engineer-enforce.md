---
description: Set up engineer-scan, RLS gate, CI workflow, pre-commit, and PR template in this repo.
---

# /engineer-enforce

Load engineer `SKILL.md` + `references/enforcement.md` (rule catalog: `references/enforcement-rules.md`).

## Execute

1. Copy into project (adjust `ENGINEER` path):
   ```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
   # Set ENGINEER to the directory containing the loaded engineer SKILL.md.
   : "${ENGINEER:?Set ENGINEER to the resolved skill directory}"
   mkdir -p scripts supabase/tests .github/workflows .github
   # Review and merge existing destination files; do not overwrite them blindly.
   cp -n "$ENGINEER/scripts/engineer-scan.sh" "$ENGINEER/scripts/check-rls-migration.sh" scripts/
   cp -n "$ENGINEER/templates/github/engineer-gates.yml" .github/workflows/
   cp -n "$ENGINEER/templates/github/pull_request_template.md" .github/
   cp -n "$ENGINEER/templates/supabase/tests/"*.sql supabase/tests/
   chmod +x scripts/engineer-scan.sh scripts/check-rls-migration.sh
   ```
2. Merge `templates/package-scripts.snippet.json` into `package.json`.
3. Recommend husky + lint-staged (see `docs/enforcement-setup.md`).
4. Target maturity **L2** unless user specifies otherwise.

## Verify

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
bash "$ENGINEER/scripts/engineer-scan.sh" --strict
```

## Report

Current maturity level, gaps, and next tier upgrades.
