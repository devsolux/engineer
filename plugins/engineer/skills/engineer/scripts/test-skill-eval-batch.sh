#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREPARE="$ROOT/scripts/prepare-skill-eval-baseline.py"
VALIDATE="$ROOT/scripts/validate-skill-eval-batch.py"
INVENTORY="$ROOT/templates/agentic/host-capabilities.sample.json"
# Standalone clean-checkout runs must not depend on prior suites.
mkdir -p "$ROOT/.engineer"
TMP="$(mktemp -d "$ROOT/.engineer/batch-test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

python3 "$PREPARE" --root "$ROOT" --inventory "$INVENTORY" --output-dir "$TMP/valid" --scenarios 121 --hosts codex,claude --activation-modes explicit,implicit >"$TMP/result.json"
python3 "$VALIDATE" "$TMP/valid/manifest.json" --root "$ROOT" >/dev/null
python3 - "$TMP/result.json" "$TMP/valid/manifest.json" <<'PY'
import json,sys
result=json.load(open(sys.argv[1])); manifest=json.load(open(sys.argv[2]))
assert result['executed'] is False and result['quota_spent'] is False
assert result['manifest'].endswith('/manifest.json') and len(result['manifest_sha256']) == 64
assert manifest['publication']['state'] == 'complete'
assert manifest['batch']['job_count'] == 4 and len(manifest['jobs']) == 4
assert {(j['host'],j['activation_mode'],j['scenario_id']) for j in manifest['jobs']} == {
 ('codex','explicit',121),('codex','implicit',121),('claude','explicit',121),('claude','implicit',121)}
assert all(j['api_key_present'] is False for j in manifest['jobs'])
PY

# Identical replay is allowed and republishes a complete manifest.
python3 "$PREPARE" --root "$ROOT" --inventory "$INVENTORY" --output-dir "$TMP/valid" --scenarios 121 --hosts codex,claude --activation-modes explicit,implicit >/dev/null
python3 "$VALIDATE" "$TMP/valid/manifest.json" --root "$ROOT" >/dev/null

# A failing arm must not publish any job or commit marker.
if python3 "$PREPARE" --root "$ROOT" --inventory "$INVENTORY" --output-dir "$TMP/invalid" --scenarios 134 --hosts codex --activation-modes explicit,implicit >/dev/null 2>&1; then
  echo "keyword-bearing implicit batch unexpectedly prepared" >&2
  exit 1
fi
if find "$TMP/invalid" -type f ! -name '.prepare.lock' | grep -q .; then
  echo "failed batch leaked a published artifact" >&2
  exit 1
fi

# An active lock prevents concurrent publication.
mkdir -p "$TMP/locked"
: >"$TMP/locked/.prepare.lock"
if python3 "$PREPARE" --root "$ROOT" --inventory "$INVENTORY" --output-dir "$TMP/locked" --scenarios 121 --hosts codex >/dev/null 2>&1; then
  echo "concurrent preparation lock was ignored" >&2
  exit 1
fi

# A non-identical existing job is never overwritten or recommitted.
python3 "$PREPARE" --root "$ROOT" --inventory "$INVENTORY" --output-dir "$TMP/collision" --scenarios 121 --hosts codex --activation-modes explicit >/dev/null
COLLISION_JOB="$(python3 - "$TMP/collision/manifest.json" "$ROOT" <<'PY'
import json,os,sys
d=json.load(open(sys.argv[1])); print(os.path.join(sys.argv[2],d['jobs'][0]['path']))
PY
)"
python3 - "$COLLISION_JOB" <<'PY'
import json,sys
p=sys.argv[1]; d=json.load(open(p)); d['budgets']['max_turns']=11; json.dump(d,open(p,'w'),indent=2)
PY
if python3 "$PREPARE" --root "$ROOT" --inventory "$INVENTORY" --output-dir "$TMP/collision" --scenarios 121 --hosts codex --activation-modes explicit >/dev/null 2>&1; then
  echo "non-identical prepared job was overwritten" >&2
  exit 1
fi
if python3 "$VALIDATE" "$TMP/collision/manifest.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "stale manifest trusted a modified job" >&2
  exit 1
fi

mutate_manifest() {
  local name="$1" expression="$2"
  python3 - "$TMP/valid/manifest.json" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$VALIDATE" "$TMP/$name.json" --root "$ROOT" >/dev/null 2>&1; then
    echo "expected batch rejection: $name" >&2
    exit 1
  fi
}

mutate_manifest missing_job 'd["jobs"].pop()'
mutate_manifest duplicate_job 'd["jobs"].append(d["jobs"][0])'
mutate_manifest forged_job_hash 'd["jobs"][0]["sha256"]="0"*64'
mutate_manifest false_execution_claim 'd["publication"]["state"]="executed"'
mutate_manifest missing_limitation 'd["limitations"].pop()'
mutate_manifest path_escape 'd["jobs"][0]["path"]="../outside.json"'
mutate_manifest malformed_identity 'd["jobs"][0]["host"]=[]'

echo "skill eval batch fixtures passed"
