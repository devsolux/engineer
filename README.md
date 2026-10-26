# Engineer

**Version 1.3.0 · Repository `devsolux/engineer` · Plugin `engineer` · Marketplace `devsolux-engineer`**

A reusable full-stack engineering skill: inspect the existing project, select a
focused workflow, make the smallest coherent change, and verify the result.
The host supplies reasoning and tool permissions. Local scripts supply bounded,
deterministic checks. There is no daemon, second model, or MCP server to deploy.

## Install

The repository is its own plugin marketplace. Both hosts read the committed
`plugins/engineer/` bundle, so installation needs no build step.

**Claude Code**

```bash
claude plugin marketplace add https://github.com/devsolux/engineer
```

```bash
claude plugin install engineer@devsolux-engineer
```

**Codex**

```bash
codex plugin marketplace add devsolux/engineer
```

```bash
codex plugin add engineer@devsolux-engineer
```

Install IDs follow `plugin@marketplace`: the plugin is `engineer` and the
marketplace is `devsolux-engineer`. `devsolux@engineer` would look for a plugin
named `devsolux` and does not resolve. The GitHub repository name is only the
marketplace source.

In Claude Code the workflows appear as `/engineer:audit`, `/engineer:fix`,
`/engineer:plan`, and so on; the `engineer` skill also activates automatically
for matching tasks. In Codex, select `$engineer` and describe the task.
Update with `claude plugin marketplace update devsolux-engineer` or
`codex plugin marketplace upgrade`; remove with `claude plugin uninstall
engineer@devsolux-engineer` or `codex plugin remove engineer@devsolux-engineer`.
See [installation and first use](docs/getting-started.md).

## Build and verify

Requirements: Python 3.10+, Bash, GNU Make, and PyYAML 6.0.3 for the complete
fixture suite. The TypeScript consumer fixtures additionally need Node.js and
`tsc` on PATH. Build and packaging themselves use Python's standard library.
See [compatibility](COMPAT.md) for tested toolchains.

```bash
make help
make setup         # optional, explicit network access: installs Python dev dependencies
make check         # syntax, integrity, security metadata, fixture bindings, static eval bank
make test          # all discovered offline shell and Python suites; no live model calls
make build         # refresh tracked plugins/engineer from canonical source
make verify-build  # fail on generated bundle drift
make package       # dist/engineer-1.3.0-plugin.zip and its SHA-256
make clean         # only .build/ and dist/; never host state, source, or .engineer/
```

For an existing environment, set `PYTHON=/path/to/python`. `make test JOBS=4`
runs suites concurrently in isolated source copies. A failing or unavailable check
must remain a failure; no success fallback is permitted.

After a reviewed runtime edit, run `make fixtures` to explicitly rebind the
**illustrative** skill-eval samples, then repeat checks and rebuild. Rebinding is
never automatic inside a verification target and is not captured execution evidence.

Publishing is explicit and separate: `make release-check` runs every offline gate,
`make github-bootstrap` creates the public repository and pushes, and
`make github-release` attaches the plugin ZIP to a tagged release. See the
[release procedure](docs/releasing.md).

## Repository layout

```text
SKILL.md                    Canonical router and single release version
commands/                   Canonical task workflows
references/                 Progressive-disclosure engineering modules
scripts/                    Deterministic tools, installers, and offline fixtures
templates/                  Consumer examples, schemas, illustrative evidence
evals/                      Static scenarios and opt-in live smoke configuration
research/                   Dated research notes behind the reference modules
packaging/plugin.json       Shared identity metadata; no independent version
plugins/engineer/           Generated install-ready plugin; committed for Git installs
.claude-plugin/             Claude marketplace catalog
.agents/plugins/            Codex marketplace catalog
docs/                       Installation, architecture, checks, releases
```

The native skill/command installers link a checkout into hosts without a plugin
marketplace and support checkout-linked development. They are an **alternative**
to marketplace install, not an additional step. See [native skills](docs/native-skills.md)
and the [command catalog](docs/slash-commands.md).

## Engineering and security boundaries

Inspect project instructions, lockfiles, architecture, and tests before choosing
frameworks or changing dependencies. Preserve detected stacks and authorized scope.
Tool availability does not imply permission to deploy, publish, spend tokens,
change production data, or install host integrations. Explicit install targets
change host state; none is a dependency of build/check/test/package.

Scanners are heuristics, not proof of absence of vulnerabilities. Captured evidence,
authorization, and state transitions must be verified outside model instructions.
See [security](SECURITY.md) and [architecture](docs/architecture.md).

[Documentation](docs/README.md) · [Module index](docs/modules.md) ·
[Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) ·
[Verification ledger](docs/verification-2026-10-11.md) · [License](LICENSE)
