#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SAMPLE="$ROOT/evals/evals.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
bash "$ROOT/scripts/run-evals.sh" --file "$SAMPLE" --full --json >/dev/null

invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$SAMPLE')); $mutation; json.dump(p,open('$TMP/$name.json','w'))"
  if bash "$ROOT/scripts/run-evals.sh" --file "$TMP/$name.json" --full >/dev/null 2>&1; then
    echo "expected invalid eval bank to fail: $name" >&2; exit 1
  fi
}
invalid_case id_gap "p['evals'][1]['id']=999"
invalid_case duplicate_prompt "p['evals'][1]['prompt']=p['evals'][0]['prompt']"
invalid_case empty_assertion "p['evals'][0]['assertions']=['']"
invalid_case duplicate_assertion "p['evals'][0]['assertions']=[p['evals'][0]['assertions'][0]]*2"
invalid_case missing_file "p['evals'][0]['files']=['references/not-real.md']"
invalid_case unsafe_file "p['evals'][0]['files']=['../outside.md']"
invalid_case unknown_field "p['evals'][0]['golden']='looks good'"
invalid_case wrong_skill "p['skill_name']='other'"
echo "eval bank fixtures passed"
