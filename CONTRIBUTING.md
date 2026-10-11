# Contributing

Read `AGENTS.md`, `SKILL.md`, and the relevant references before making changes.
Edit canonical source, not `plugins/engineer/`. Keep one owner per responsibility:
host reasoning; skill routing; deterministic validation; host-specific packaging.

Preserve existing user edits. Do not introduce network/model calls into offline
checks. Never suppress failed verification or re-label illustrative evidence as
captured execution. Add a regression test named `scripts/test-*.py` or
`scripts/test-*.sh`; the runner discovers both automatically.

```bash
make lint
make fixtures    # only after reviewing intended source/fixture changes
make check
make test
make build
make verify-build
make package
```

Review generated diffs and the SHA-256 output. Keep release version in SKILL.md
metadata and synchronize documentation headers. Avoid floating executable
package commands and Action revisions. Dependency upgrades require explicit pins,
primary-source verification, and a passing compatible test environment.

Tests can create isolated temporary Git repositories; they must never commit,
push, install into the real home directory, or call an authenticated model host.
Build/check targets must not publish or install plugins. Report actual commands,
results, and limitations with the change. See [release procedure](docs/releasing.md).
