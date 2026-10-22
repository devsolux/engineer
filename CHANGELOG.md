# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/); the single release version lives in
`SKILL.md` metadata.

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
