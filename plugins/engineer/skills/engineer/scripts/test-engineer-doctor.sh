#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCTOR="$ROOT/scripts/engineer-doctor.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

for rel in .cursor .claude .codex .agents .hermes .config/opencode .gemini .grok; do
  mkdir -p "$TMP/$rel/skills"
  ln -s "$ROOT" "$TMP/$rel/skills/engineer"
done
python3 "$ROOT/scripts/install-host-activation.py" --home "$TMP" --hosts all >/dev/null
python3 "$DOCTOR" --root "$ROOT" --home "$TMP" --json --strict --require-activation >"$TMP/report.json"
python3 - "$TMP/report.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['decision']=='healthy'
assert len(d['installations'])==8 and all(x['status']=='current' for x in d['installations'])
assert len(d['activation_adapters'])==8 and all(x['status']=='current' for x in d['activation_adapters'])
assert all(x['mode']=='symlink' and x['canonical_target'] for x in d['installations'])
assert d['privacy']=={'secret_values_read':False,'host_config_read':False,'session_content_read':False,'telemetry_content_read':False}
PY

rm "$TMP/.gemini/skills/engineer"
if python3 "$DOCTOR" --root "$ROOT" --home "$TMP" --strict >/dev/null 2>&1; then
  echo "missing installation unexpectedly passed strict doctor" >&2
  exit 1
fi

mkdir -p "$TMP/.gemini/skills/engineer"
printf '%s\n' '---' 'name: engineer' 'metadata:' '  version: "0.0.0"' '---' >"$TMP/.gemini/skills/engineer/SKILL.md"
if python3 "$DOCTOR" --root "$ROOT" --home "$TMP" --strict >/dev/null 2>&1; then
  echo "stale installation unexpectedly passed strict doctor" >&2
  exit 1
fi

rm -rf "$TMP/.gemini/skills/engineer"
ln -s "$ROOT" "$TMP/.gemini/skills/engineer"
rm "$TMP/.cursor/rules/engineer-auto.mdc"
if python3 "$DOCTOR" --root "$ROOT" --home "$TMP" --strict --require-activation >/dev/null 2>&1; then
  echo "missing activation adapter unexpectedly passed strict doctor" >&2
  exit 1
fi

echo "engineer doctor fixtures passed"
