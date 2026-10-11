---
description: Audit and operate a proportional open-source GitHub repository baseline
argument-hint: "[repository path]"
---

Load `references/oss-maintainer.md`, `references/git-signing-deploy.md`, `references/enforcement.md`, and `references/output-quality.md`.

1. Confirm OSS/public status from explicit user context or host API; local license files are signals, not proof.
2. Classify the project as experimental, supported, critical, or deprecated and run `python3 "$ENGINEER/scripts/audit-oss-repo.py" <target> --visibility public --profile <profile> --json`. Unknown visibility fails closed; confirmed private repositories remain outside automatic OSS mode unless the user explicitly scopes an OSS migration.
3. When the task authorizes repository changes, run `python3 "$ENGINEER/scripts/apply-oss-baseline.py" <target> --visibility public --apply --output <receipt.json> --json`, then independently replay it with `python3 "$ENGINEER/scripts/validate-oss-application.py" <receipt.json> --root <target>`. It creates only missing deterministic local files, never overwrites project content, and emits conflicts plus project decisions still required. Re-run the audit after validation.
4. Inspect effective GitHub settings before claims. Ask before changing visibility, rulesets, access, vulnerability reporting, releases, packages or other external state.
5. Validate project-native tests plus Engineer supply-chain, signing, output-quality and release gates. Report exceptions and evidence limitations.
