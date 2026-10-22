# Release procedure

1. Review source changes, threat boundaries, and dependency evidence. Update the
   single `SKILL.md` version, `CHANGELOG.md`, and the version headers in
   `docs/README.md` and `docs/modules.md`. Do not redate research notes without
   rechecking their sources. Run `python3 scripts/report-module-currency.py`: every
   module past its review cadence is re-verified against primary sources (then redated)
   or listed as past-due in the dated verification ledger — never redated blind.
2. Rebind only reviewed illustrative fixtures (`make fixtures`), then run
   `make build` and review the generated `plugins/engineer/` diff.
3. Run `make release-check` (`check`, `test`, and `verify-build`). Review failures
   rather than loosening assertions.
4. With the Claude CLI available, run `make host-validate` (strict manifest
   validation). Install from the local checkout into a disposable host profile,
   invoke a read-only workflow, update, and remove it. Record host version, OS,
   and observed results in a dated verification ledger.
5. Publish only after explicit authorization:
   - first publication: `make github-bootstrap` (runs the gates, creates the
     public `devsolux/engineer` repository, and pushes `main`);
   - later changes: `make github-push GITHUB_COMMIT_MSG='…'`;
   - tagged release with the plugin ZIP: `make github-release`.
6. After publishing, install from GitHub with the commands in the README and
   confirm both hosts resolve `engineer@devsolux-engineer` at the new version, and
   that `git ls-remote --tags origin` lists `v<version>`; record both in the ledger.

Version is read from `SKILL.md`. The ZIP has sorted paths, fixed timestamps, explicit
file modes, no symlinks, and a SHA-256 sidecar. Rebuilding identical input should
produce identical bytes in the same Python/zlib toolchain; do not claim compressed
byte equivalence across untested zlib versions. The hash verifies transfer
integrity, not identity or trust. Sign or pin a reviewed release through your
supply-chain policy if required.

The installable ZIP has plugin metadata at its root. The Git repository also
includes the marketplace catalogs. These are different artifacts. Neither is an
MCPB or proof of public marketplace approval.

## Host smoke acceptance

Both hosts must discover `engineer` in `devsolux-engineer`, load the same canonical
skill, preserve user approvals, and complete the chosen read-only task. A second
install or update must not duplicate tools or overwrite unrelated state. Validate
in the intended desktop or CLI surface, not merely in a manifest parser. Offline
fixture success does not waive these checks.
