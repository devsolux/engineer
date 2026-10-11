#!/usr/bin/env bash
# Negative fixtures for repository drift detection.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

copy_repo() {
  local dest="$1"
  mkdir -p "$dest"
  tar -C "$ROOT" --exclude=.git --exclude=.engineer --exclude=.build --exclude=dist --exclude=.venv --exclude=node_modules --exclude=plugins -cf - . | tar -C "$dest" -xf -
}

expect_fail() {
  local name="$1"
  local dir="$2"
  if bash "$dir/scripts/validate-repo.sh" >/dev/null 2>&1; then
    echo "  ✗ $name was not detected"
    exit 1
  fi
  echo "  ✓ $name detected"
}

echo "engineer test-repo-validation — negative fixtures"
echo "---"

copy_repo "$TMP/command"
rm "$TMP/command/commands/engineer-kpi.md"
expect_fail "documented command without file" "$TMP/command"

copy_repo "$TMP/manifest"
printf '\n| `missing-module.md` | negative fixture |\n' >> "$TMP/manifest/references/MANIFEST.md"
expect_fail "missing MANIFEST reference" "$TMP/manifest"

copy_repo "$TMP/version"
VERSION=$(sed -n 's/^  version: "\([^"]*\)"$/\1/p' "$TMP/version/SKILL.md" | head -1)
sed -i.bak "s/$VERSION/0.0.0/" "$TMP/version/docs/README.md"
rm -f "$TMP/version/docs/README.md.bak"
expect_fail "human-doc version drift" "$TMP/version"

copy_repo "$TMP/implicit-policy"
sed -i.bak 's/allow_implicit_invocation: true/allow_implicit_invocation: false/' "$TMP/implicit-policy/agents/openai.yaml"
rm -f "$TMP/implicit-policy/agents/openai.yaml.bak"
expect_fail "disabled implicit invocation" "$TMP/implicit-policy"

copy_repo "$TMP/trigger-prefix"
sed -i.bak 's/automatically activates/handles/' "$TMP/trigger-prefix/SKILL.md"
rm -f "$TMP/trigger-prefix/SKILL.md.bak"
expect_fail "implicit trigger moved out of front-loaded metadata" "$TMP/trigger-prefix"

copy_repo "$TMP/oversize"
for _ in $(seq 1 120); do printf 'Filler rule line for the oversize fixture.\n'; done \
  >> "$TMP/oversize/references/frontend.md"
expect_fail "reference module over the 300-line budget" "$TMP/oversize"

copy_repo "$TMP/verb-budget"
sed -i.bak 's/| decision-engineering + domain modules |/| deep-research + python + frontend + backend-api + backend-auth |/' \
  "$TMP/verb-budget/SKILL.md"
rm -f "$TMP/verb-budget/SKILL.md.bak"
expect_fail "verb load budget blowout" "$TMP/verb-budget"

copy_repo "$TMP/orphan-ref"
printf '# Orphan fixture\n\nNot registered in MANIFEST.\n' > "$TMP/orphan-ref/references/orphan-fixture.md"
expect_fail "orphan reference module absent from MANIFEST" "$TMP/orphan-ref"

copy_repo "$TMP/repo-escape"
printf '\nResearch baseline: `../../private-workspace-pack/report.md`\n' \
  >> "$TMP/repo-escape/references/composition.md"
expect_fail "repo-escaping ../../ pointer path" "$TMP/repo-escape"

copy_repo "$TMP/toc-missing"
for _ in $(seq 1 90); do printf 'Filler guidance line for the TOC fixture.\n'; done \
  >> "$TMP/toc-missing/references/agentic-engineering.md"
expect_fail "long reference module without a TOC" "$TMP/toc-missing"

# No module is exempt from the TOC rule; a formerly exempt module must be caught too.
copy_repo "$TMP/toc-exemption"
python3 - <<'PY' "$TMP/toc-exemption/references/ai-evals.md"
from pathlib import Path
import re
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
stripped = re.sub(r"^## Contents\n(?:- \[.*\n)+\n", "", text, count=1, flags=re.M)
assert stripped != text, "fixture expects a Contents block in ai-evals.md"
path.write_text(stripped, encoding="utf-8")
PY
expect_fail "formerly exempt long module without a TOC" "$TMP/toc-exemption"

copy_repo "$TMP/script-mention"
printf '\nGhost tool: `scripts/ghost-tool.sh` (fixture; not in MANIFEST).\n' \
  >> "$TMP/script-mention/SKILL.md"
expect_fail "SKILL.md script mention missing from MANIFEST" "$TMP/script-mention"

copy_repo "$TMP/last-verified"
python3 - <<'PY' "$TMP/last-verified/references/frontend.md"
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
path.write_text(text.replace("**Last verified**", "**Reviewed**", 1), encoding="utf-8")
PY
expect_fail "reference module missing Last verified" "$TMP/last-verified"

copy_repo "$TMP/operator-leak"
printf '\nWhen publishing via x_article_publish.py, require personal-brand/research/articles paths.\n' \
  >> "$TMP/operator-leak/SKILL.md"
expect_fail "operator publishing runbook in SKILL.md" "$TMP/operator-leak"

echo "---"
echo "OK — all repository drift fixtures passed"
