#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
# Bash 3.2 (macOS) does not exit on a failing [[ ]] under set -e, and no bash exits on a
# failing `! cmd`, so every assertion ends in an explicit fail.
fail() { echo "FAIL: $*" >&2; exit 1; }

mkdir -p "$TMP/.claude" "$TMP/.grok" "$TMP/.hermes/memories"
printf '%s\n' '# existing Claude rule' > "$TMP/.claude/CLAUDE.md"
printf '%s\n' '# existing Grok rule' > "$TMP/.grok/AGENTS.md"
printf '%s\n' '# existing Hermes memory' > "$TMP/.hermes/memories/MEMORY.md"

python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all >/dev/null
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all >/dev/null
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all --check >/dev/null

[[ "$(grep -c '<!-- engineer-auto:begin -->' "$TMP/.claude/CLAUDE.md")" -eq 1 ]] || fail "reinstall duplicated the Claude block"
grep -q '# existing Claude rule' "$TMP/.claude/CLAUDE.md"
grep -q '# existing Grok rule' "$TMP/.grok/AGENTS.md"
grep -q '^alwaysApply: true$' "$TMP/.cursor/rules/engineer-auto.mdc"

python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all --remove >/dev/null
grep -q '# existing Claude rule' "$TMP/.claude/CLAUDE.md"
grep -q '# existing Grok rule' "$TMP/.grok/AGENTS.md"
grep -q '# existing Hermes memory' "$TMP/.hermes/memories/MEMORY.md"
for kept in .claude/CLAUDE.md .grok/AGENTS.md .hermes/memories/MEMORY.md; do
  if grep -q 'engineer-auto:begin' "$TMP/$kept"; then fail "remove left the Engineer block in $kept"; fi
done
[[ ! -e "$TMP/.cursor/rules/engineer-auto.mdc" ]] || fail "remove left the Cursor rule"
# Files that held only Engineer's block are deleted, never left behind as blank files.
for created in AGENTS.md .codex/AGENTS.md .gemini/GEMINI.md .config/opencode/AGENTS.md; do
  [[ ! -e "$TMP/$created" ]] || fail "remove left a blank $created behind"
done
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all --remove >/dev/null

# Codex reads its global file from CODEX_HOME (~/.codex); no case-variant duplicates are written.
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts codex,claude >/dev/null
grep -q 'engineer-auto:begin' "$TMP/.codex/AGENTS.md"
[[ ! -e "$TMP/AGENTS.md" ]] || fail "codex install wrote a home-level AGENTS.md"
ls "$TMP/.claude" | grep -qx 'CLAUDE.md'
[[ "$(ls "$TMP/.claude" | grep -ic '^claude\.md$')" -eq 1 ]] || fail "case-variant CLAUDE.md duplicate"
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts codex,claude --remove >/dev/null

# A dotfile-managed (symlinked) rule file keeps its link; the real file is updated in place.
mkdir -p "$TMP/dotfiles"
printf '%s\n' '# managed by dotfiles' > "$TMP/dotfiles/CLAUDE.md"
rm "$TMP/.claude/CLAUDE.md"
ln -s "$TMP/dotfiles/CLAUDE.md" "$TMP/.claude/CLAUDE.md"
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts claude >/dev/null
[[ -L "$TMP/.claude/CLAUDE.md" ]] || fail "install replaced the dotfile symlink"
grep -q 'engineer-auto:begin' "$TMP/dotfiles/CLAUDE.md"
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts claude --remove >/dev/null
[[ -L "$TMP/.claude/CLAUDE.md" ]] || fail "remove replaced the dotfile symlink"
grep -q '# managed by dotfiles' "$TMP/dotfiles/CLAUDE.md"
if grep -q 'engineer-auto:begin' "$TMP/dotfiles/CLAUDE.md"; then fail "remove left the block in the dotfile"; fi

# A symlinked file that held only Engineer's block keeps its link and an empty target.
printf '' > "$TMP/dotfiles/GEMINI.md"
mkdir -p "$TMP/.gemini"
ln -s "$TMP/dotfiles/GEMINI.md" "$TMP/.gemini/GEMINI.md"
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts gemini >/dev/null
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts gemini --remove >/dev/null
[[ -L "$TMP/.gemini/GEMINI.md" && -f "$TMP/dotfiles/GEMINI.md" ]] || fail "remove deleted a symlinked rule file"

# Without --home, profile overrides choose the file (hermetic via an isolated HOME).
HOME="$TMP/profile-home" CODEX_HOME="$TMP/codex-profile" \
  python3 "$ROOT/scripts/install-host-activation.py" --hosts codex >/dev/null
grep -q 'engineer-auto:begin' "$TMP/codex-profile/AGENTS.md"
[[ ! -e "$TMP/profile-home/.codex/AGENTS.md" ]] || fail "profile override ignored"

echo "OK host activation install/check/remove is idempotent and preserves existing content"
