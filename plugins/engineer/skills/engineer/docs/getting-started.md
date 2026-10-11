# Installation and first use

## Identity

Repository: `devsolux/engineer` (public). Plugin: `engineer`. Marketplace:
`devsolux-engineer`. The install identifier is `engineer@devsolux-engineer`
(`plugin@marketplace`); it is not the GitHub `owner/repository` pair.

The repository root carries both marketplace catalogs and the generated
`plugins/engineer/` directory, so a Git marketplace install needs no build step.

## Claude Code

```bash
claude plugin marketplace add https://github.com/devsolux/engineer
```

```bash
claude plugin install engineer@devsolux-engineer
```

Start a new session (or restart Claude Code) after installing. Workflows appear
as `/engineer:audit`, `/engineer:fix`, `/engineer:plan`, and the rest of the
[command catalog](slash-commands.md); the `engineer` skill also activates
automatically for matching software tasks.

## Codex

```bash
codex plugin marketplace add devsolux/engineer
```

```bash
codex plugin add engineer@devsolux-engineer
```

Select `$engineer` and describe the task, or let implicit invocation route a
matching request.

## Local checkout

To install this working tree instead of GitHub, run `make install-claude-local`
or `make install-codex-local`. These targets change the selected host's
configuration. Do not combine a native install and a marketplace install for the
same host unless you are deliberately testing duplicate discovery.

## First task

Try `/engineer:audit` (Claude Code) or `$engineer` with a read-only review request
(Codex). Confirm which skill and command files were actually loaded; a marketplace
listing alone does not prove activation.

Use the minimum host permissions. The plugin does not require an API key or MCP
endpoint of its own. A workflow using external providers still requires the
provider's genuine permissions and explicit approval for costly or consequential
operations. Instructions cannot grant those permissions.

## Updates and removal

| Action | Claude Code | Codex |
|---|---|---|
| Refresh catalog | `claude plugin marketplace update devsolux-engineer` | `codex plugin marketplace upgrade` |
| Update plugin | `claude plugin update engineer@devsolux-engineer` | `codex plugin add engineer@devsolux-engineer` |
| Remove plugin | `claude plugin uninstall engineer@devsolux-engineer` | `codex plugin remove engineer@devsolux-engineer` |
| Remove catalog | `claude plugin marketplace remove devsolux-engineer` | `codex plugin marketplace remove devsolux-engineer` |

Native checkout links and aliases have separate receipt-aware uninstallers; see
[native skills](native-skills.md). `make clean` does not uninstall anything.

Desktop, CLI, web, and managed workspace surfaces differ. See
[compatibility](../COMPAT.md) for what has been verified.
