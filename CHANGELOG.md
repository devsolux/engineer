# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/); the single release version lives in
`SKILL.md` metadata.

## Unreleased

### Added

- MCP 2026-07-28 ("stateless core") evidence: `compile-mcp-transcript.py`,
  `validate-mcp-session.py` and `validate-mcp-content.py` now validate stateless transcripts
  and receipts, chosen by the per-request `_meta` protocol version, next to the unchanged
  2025-11-25 handshake path. Stateless rules: no `initialize` or session id, one version per
  transcript with matching HTTP version headers, optional `server/discover` (its capabilities
  bound later operations; its instructions quarantine), required `resultType`, `ttlMs` and
  `cacheScope` on cacheable results, stable client/server identity, and rejection of
  `input_required`, task results, task methods, a negotiated tasks extension, and
  `subscriptions/listen`. Roots, Sampling, Logging and dynamic client registration exposure is
  recorded as `deprecated_feature_exposure` and must be acknowledged in the session receipt; a
  stateless receipt without a captured `server/discover`, or with a discovered server extension,
  is gated.
- Synthetic fixtures under `templates/agentic/mcp-evidence-2026-07-28/`, the
  `mcp-session-2026-07-28.sample.json` and `mcp-content-2026-07-28.sample.json` receipts, and
  stateless mutation cases in `test-mcp-transcript.sh`, `test-mcp-session.sh` and
  `test-mcp-content.sh`.
- `engineer fix --findings <run>/findings.json`: remediation from a validated security-audit
  receipt, traceable from fingerprint to fix to regression test. Only `confirmed` records are
  fixed, in severity order, one per atomic change at the record's remediation layer and paths,
  each behind a regression test built from the trace and boundary that fails before the repair
  and passes after; `needs_validation` records are never patched (their local plan runs in a
  sandbox or the owner-observed checks go back to the user, and a vulnerable result returns to
  the audit for re-verification); `rejected` records are skipped and listed. Documented in the
  fix command, a "From findings to fixes" section of `security-audit.md`, and a pointer in
  `root-cause-engineering.md`.
- `validate-security-findings.py --remediated remediation.json`: cross-checks the fix receipt
  against the findings it binds by digest (confirmed only, severity order, changed paths inside
  `remediation.paths`, the matching layer, a red-then-green regression test, passing
  verification commands, a declared mitigation when not root-cause fixed, every record
  accounted for exactly once), with an illustrative
  `templates/agentic/security-remediation.sample.json`, mutation cases, and two eval
  scenarios (215, 216).

### Changed

- A 2026-07-28 version negotiated through `initialize`, mixed versions, and a receipt whose
  version differs from its compiled transcript are rejected, never downgraded; so is a content
  receipt whose capture manifest version differs from its bound session. The previous blanket
  rejection of every 2026-07-28 input is gone. `mcp-security.md` (Contract), `COMPAT.md` and the
  mcp-audit command describe both validated revisions.

### Fixed

- `compile-mcp-transcript.py` rejected a non-object JSON-RPC `result` with a Python traceback;
  it now reports `captured result invalid: <method>` (regression case in `test-mcp-transcript.sh`).

## 1.1.0 — 2026-10-22

### Added

- `engineer security-audit <target>`: an evidence-graded codebase vulnerability audit —
  guidance mode by default, a six-phase full run (reconnaissance, coverage ledger, isolated
  hunting waves, refutation by a verifier that did not hunt, three-verdict `findings.json`,
  independent record review, target-neutral report) on request. Ships as three reference
  modules (`security-audit.md`, `security-attack-classes.md`, `security-audit-domains.md`),
  the `/engineer-security-audit` command, four role prompt bodies, the
  `validate-security-findings.py` and `validate-security-coverage.py` validators, the
  `security-ledger.py` ledger tool, illustrative receipts with bound evidence, JSON schemas,
  regression suites, and six static eval scenarios. Severity exists only on confirmed records
  and never exceeds demonstrated impact; target code runs only in an OS-enforced sandbox.
- `scripts/report-module-currency.py`: reference-module review-cadence report, printed
  informationally by `validate-repo.sh`, with a `--fail-after-days N` gate mode.
- `scan-doc-supply-chain.py`: a `privileged-trigger-fork-checkout` rule
  (`pull_request_target` / `workflow_run` checking out fork code) and YAML-fence scanning in
  Markdown; the CI template now ships the documented `supply-chain` job.

### Changed

- Currency (2026-10-22 ledger): Next 15 end-of-life (2026-10-21) and the Node 24 → 26 LTS
  handoff in `COMPAT.md`, stack rules, project detection, deploy-ops and the CI template; the
  repository workflow runs on push to `main` and on pull requests with a Node 26 lane; host
  versions and the Claude Code 2.1.304 hook limits in `coding-agent-hosts.md`.
- MCP: `mcp-security.md` and the mcp-audit command re-verified against the 2026-07-28 revision
  (stateless core; Roots, Sampling, Logging and dynamic client registration deprecated; Tasks
  as an optional extension). The transcript compiler and session validator reject a
  2026-07-28 input with an explicit message instead of a generic one; fixtures stay on
  2025-11-25 as declared scenario inputs.
- One severity mapping across surfaces (`code-quality.md`) and a confidence tag in the
  `engineer audit` template; live-eval reports record whether the model was an alias or a
  pinned id; release and contribution docs state the module-currency policy.
- Web-search strategy packs translated to English with currency headers.

### Fixed

- Documentation that disagreed with code: documented workflows now pin `gitleaks-action`,
  `actions/checkout` and `supabase/setup-cli` by commit; `oss-maintainer.md` lists the WORM
  leak class; the enforce command no longer repeats its guard line; enforcement docs match
  the shipped CI template; eval 169 names 2026-07-28 as the current MCP revision; the
  2026-10-11 ledger's "public repository does not exist yet" statement is superseded.

## 1.0.0 — 2026-10-11

Initial public release.

- `engineer` skill: a progressive-disclosure router (`SKILL.md`) over 108 reference
  modules and 51 task workflows covering planning, auditing, building, fixing,
  refactoring, design, security, testing, research, and shipping.
- Plugin distribution from the public `devsolux/engineer` repository: Claude Code
  and Codex marketplace catalogs (`devsolux-engineer`) serving one generated
  bundle, `plugins/engineer`, installable as `engineer@devsolux-engineer` with no
  build step. Claude commands appear as `/engineer:<workflow>` with descriptions
  taken from the canonical workflows.
- Deterministic, standard-library plugin builder with ownership and drift checks,
  reproducible ZIP packaging with a SHA-256 sidecar, drift reports that name the
  missing, unexpected, or changed generated files, and desktop metadata files
  (`.DS_Store`, `._*`) ignored rather than blocking rebuilds.
- Offline verification: source linting, repository structure and supply-chain
  checks, a 208-scenario static eval bank, and 51 isolated test suites wired
  through `make` and a pinned GitHub Actions matrix (Linux/macOS, Python 3.10/3.13).
- Optional native skill and command installers for hosts without plugin
  marketplaces, with receipt-owned uninstall.
- Explicit publishing targets: `make release-check`, `make github-bootstrap`
  (public repository), and `make github-release`.
