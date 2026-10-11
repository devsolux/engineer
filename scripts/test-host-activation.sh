#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/.claude" "$TMP/.grok" "$TMP/.hermes/memories"
printf '%s\n' '# existing Claude rule' > "$TMP/.claude/CLAUDE.md"
printf '%s\n' '# existing Grok rule' > "$TMP/.grok/AGENTS.md"
printf '%s\n' '# existing Hermes memory' > "$TMP/.hermes/memories/MEMORY.md"

python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all >/dev/null
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all >/dev/null
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all --check >/dev/null

[[ "$(grep -c '<!-- engineer-auto:begin -->' "$TMP/.claude/CLAUDE.md")" -eq 1 ]]
grep -q '# existing Claude rule' "$TMP/.claude/CLAUDE.md"
grep -q '# existing Grok rule' "$TMP/.grok/AGENTS.md"
grep -q '^alwaysApply: true$' "$TMP/.cursor/rules/engineer-auto.mdc"

python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all --remove >/dev/null
grep -q '# existing Claude rule' "$TMP/.claude/CLAUDE.md"
! grep -q 'engineer-auto:begin' "$TMP/.claude/CLAUDE.md"
[[ ! -e "$TMP/.cursor/rules/engineer-auto.mdc" ]]

# Codex reads its global file from CODEX_HOME (~/.codex); no case-variant duplicates are written.
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts codex,claude >/dev/null
grep -q 'engineer-auto:begin' "$TMP/.codex/AGENTS.md"
[[ ! -e "$TMP/AGENTS.md" ]]
ls "$TMP/.claude" | grep -qx 'CLAUDE.md'
[[ "$(ls "$TMP/.claude" | grep -ic '^claude\.md$')" -eq 1 ]]
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts codex,claude --remove >/dev/null

# A dotfile-managed (symlinked) rule file keeps its link; the real file is updated in place.
mkdir -p "$TMP/dotfiles"
printf '%s\n' '# managed by dotfiles' > "$TMP/dotfiles/CLAUDE.md"
rm "$TMP/.claude/CLAUDE.md"
ln -s "$TMP/dotfiles/CLAUDE.md" "$TMP/.claude/CLAUDE.md"
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts claude >/dev/null
[[ -L "$TMP/.claude/CLAUDE.md" ]]
grep -q 'engineer-auto:begin' "$TMP/dotfiles/CLAUDE.md"
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts claude --remove >/dev/null
[[ -L "$TMP/.claude/CLAUDE.md" ]]
grep -q '# managed by dotfiles' "$TMP/dotfiles/CLAUDE.md"
! grep -q 'engineer-auto:begin' "$TMP/dotfiles/CLAUDE.md"

# Without --home, profile overrides choose the file (hermetic via an isolated HOME).
HOME="$TMP/profile-home" CODEX_HOME="$TMP/codex-profile" \
  python3 "$ROOT/scripts/install-host-activation.py" --hosts codex >/dev/null
grep -q 'engineer-auto:begin' "$TMP/codex-profile/AGENTS.md"
[[ ! -e "$TMP/profile-home/.codex/AGENTS.md" ]]

echo "OK host activation install/check/remove is idempotent and preserves existing content"
