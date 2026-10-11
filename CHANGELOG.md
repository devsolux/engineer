# Changelog

All notable changes to this project are documented here. The project follows
[Semantic Versioning](https://semver.org/); the single release version lives in
`SKILL.md` metadata.

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
