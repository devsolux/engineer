# Verification ledger — 2026-10-11

Release 1.0.0 was verified on macOS 27.0.1 (arm64) with Python 3.11.17,
PyYAML 6.0.3, Node 24.21.0, TypeScript 5.8.3, Bash 3.2.57, and GNU Make 3.81.
Research notes keep their own dates; this ledger does not re-verify them.

## Executed checks

| Check | Result |
|---|---|
| `make check` (source lint, repository structure, supply-chain, fixture bindings, 208 static eval scenarios) | Passed |
| `make test JOBS=6` (51 isolated offline suites, empty HOME per suite) | 51/51 passed |
| `make verify-build` and `make package` | No drift; deterministic ZIP and SHA-256 produced |
| `claude plugin validate --strict` on the marketplace and the plugin (Claude Code 2.1.282) | Passed |
| Local-marketplace install into throwaway Claude Code and Codex homes | `engineer@devsolux-engineer` 1.0.0 installed and enabled on both |
| Public-repository install replay: a commit of exactly the Git-publishable tree, served for `https://github.com/devsolux/` through a temporary `url.insteadOf` rewrite | `claude plugin marketplace add https://github.com/devsolux/engineer` + `claude plugin install engineer@devsolux-engineer`, and `codex plugin marketplace add devsolux/engineer` + `codex plugin add engineer@devsolux-engineer` both succeeded |
| Installed components | Claude Code: `engineer` skill plus 50 `/engineer:*` commands; Codex 0.162.0-alpha.17.2: skill registered as `engineer:engineer` (rendered with `codex debug prompt-input`, no model call) |
| Update and removal commands in the README and getting-started guide | All succeeded on both hosts |
| `engineer-doctor.py` run from the installed plugin cache | Both marketplace copies reported `current`; decision `healthy` |
| Installer chain under the stock macOS Python 3.9.6 | Imports and `--help` succeed |

Claude Code's plugin loader substitutes `${CLAUDE_PLUGIN_ROOT}` and `$ARGUMENTS` in
plugin command bodies; this was confirmed in the 2.1.282 loader source, not by a
model run.

## Sources checked

| Area | Confirmed / applied | Primary source |
|---|---|---|
| Claude marketplace and plugin layout | `<plugin>@<marketplace>`; root catalog with a relative plugin source; `.claude-plugin/plugin.json` | Claude Code 2.1.282 CLI (`claude plugin --help`, strict validation, installs above) |
| Codex plugins | `codex plugin marketplace add` (owner/repo, Git URL, or local path) and `codex plugin add PLUGIN@MARKETPLACE` | `codex plugin --help` (0.162.0-alpha.17.2) |
| GitHub Action pins | Each pinned commit equals its tag and is the latest release: checkout v7.0.1 `3d3c42e5`, setup-python v7.0.0 `5fda3b95`, setup-node v7.1.0 `949feb24`, upload-artifact v7.0.2 `cf430e03`, attest v4.2.2 `1e69f48a`, gitleaks-action v3.0.0 `e0c47f4f` | GitHub REST API (`git/ref/tags`, `releases/latest`) |
| TypeScript | 7.0.2 is `latest`; 5.8.3 baseline still published | npm registry |
| PyYAML | 6.0.3 is the newest release | PyPI |

## Not established

- The public repository does not exist yet; installation from the real GitHub
  remote must be repeated after `make github-bootstrap`.
- Linux, Python 3.10/3.13, and TypeScript 7.0.2 run only in GitHub Actions CI.
- No authenticated model session was run, so live skill activation quality,
  desktop app surfaces, and browser-driven templates remain unverified here.
