# Enforcement setup

Read the target repository instructions, scripts, lockfile, and CI before copying
anything. Review `templates/github/engineer-gates.yml` and the package-script
snippet against the existing application. They are examples, not drop-in proof
that the project's dependencies and test commands exist.

Resolve `ENGINEER` to the actual loaded skill directory. Keep the shell working
directory in the application being inspected; do not accidentally scan the plugin.

```bash
: "${ENGINEER:?Set ENGINEER to the loaded skill directory}"
bash "$ENGINEER/scripts/engineer-scan.sh" --strict
```

A nonzero result blocks completion. Do not append a successful fallback or suppress
stderr. `--strict` enables default design and backend coverage unless an explicit
domain flag selects a narrower check. The scanner is heuristic: passing it does
not replace authorization tests, tenant isolation, migrations, dependency scanning,
or a human security review where appropriate.

Only copy the requested scanner/migration checker, not every test and maintenance
script. Merge existing CI and package scripts rather than overwriting them. Keep
Action references immutable and project dependency installation lockfile-based.
State unavailable verification as blocked, with the exact missing prerequisite.

Health scoring is advisory by default. Use its explicit `--strict` option when an
exit-code gate is required. Never interpret a health score as security certification.
