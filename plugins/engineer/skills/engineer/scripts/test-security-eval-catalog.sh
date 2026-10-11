#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-security-eval-catalog.py"
SAMPLE="$ROOT/templates/agentic/security-eval-catalog.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 "$VALIDATOR" "$SAMPLE" --json | python3 -c 'import json,sys; assert json.load(sys.stdin)["ok"]'

invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$SAMPLE')); $mutation; json.dump(p,open('$TMP/$name.json','w'))"
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected invalid security catalog to fail: $name" >&2; exit 1
  fi
}
invalid_case live_target "p['authorization']['live_targets']=True"
invalid_case real_network "p['authorization']['network']='unrestricted'"
invalid_case destructive_enabled "p['authorization']['destructive_actions_disabled']=False"
invalid_case missing_category "p['cases']=[c for c in p['cases'] if c['category']!='supply_chain']"
invalid_case missing_benign_pair "[c.pop('benign_case_id',None) for c in p['cases'] if c['id']=='attack_goal_hijack']"
invalid_case bad_canary "p['cases'][0]['inert_canary']='secret'"
invalid_case operational_payload "p['cases'][3]['payload']='not allowed'"
invalid_case live_url "p['cases'][3]['scenario']='Open https://example.invalid'"
invalid_case credential_shape "p['cases'][3]['scenario']='Use sk-abcdefghijklmnop'"
invalid_case nonfixture_target "p['cases'][3]['fixture']='production/service'"
invalid_case no_cleanup "p['cases'][3]['cleanup']=[]"
invalid_case duplicate_regression "p['cases'][4]['regression_id']=p['cases'][3]['regression_id']"
echo "security eval catalog fixtures passed"
