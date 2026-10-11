# Native skill installation (alternative to marketplace packaging)

The existing installer links one reviewed checkout into supported native skill
roots. Keep that checkout available: relocating or deleting it can break the links.
A native link is not a plugin package, marketplace registration, or copied release.

```bash
bash scripts/install-all-agents.sh --hosts claude,codex --dry-run
bash scripts/install-all-agents.sh --hosts claude,codex
bash scripts/install-commands.sh --hosts claude,codex --dry-run
bash scripts/install-commands.sh --hosts claude,codex
```

Installation is explicit. `--home /path/to/isolated-home` permits hermetic tests and
ignores profile overrides. The installer supports the host inventory in
`scripts/skill_hosts.py`; missing CLI executables are not proof of host support.
Use `--hosts` to avoid accidental auto-selection. Inspect `--help` for all options.

Codex/shared native skills use `~/.agents/skills/engineer`; Claude uses
`~/.claude/skills/engineer` (or the supported profile override). The installer
rejects conflicting existing paths. Do not remove someone else's skill to force
installation. Moving a checkout requires an explicit repair of stale links.

Native command aliases are separate, receipt-owned generated adapters. Codex
aliases use `/prompts:engineer-*`; other supported adapters generally use
`/engineer-*`. These differ from Claude plugin namespace commands such as
`/engineer:audit`. Prefer native skill selection where host prompt aliases are
unsupported or deprecated. Actual host behavior must be smoke-tested.

```bash
bash scripts/install-commands.sh --hosts claude,codex --check
bash scripts/install-commands.sh --hosts claude,codex --uninstall
bash scripts/install-all-agents.sh --hosts claude,codex --uninstall
```

The alias uninstaller removes only unchanged receipt-owned files. The skill
uninstaller removes only links pointing to this checkout. Neither should erase
user-managed files, and neither affects marketplace installations.
