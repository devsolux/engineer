#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VALIDATOR="$SCRIPT_DIR/validate-product-metrics.py"
SAMPLE="$ROOT/templates/product-metrics/measurement-plan.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 -m json.tool "$ROOT/templates/product-metrics/measurement-plan.schema.json" >/dev/null
python3 "$VALIDATOR" "$SAMPLE" >/dev/null
python3 "$VALIDATOR" "$SAMPLE" --json | python3 -c 'import json,sys; assert json.load(sys.stdin)["ok"]'

invalid_case() {
  local name="$1"
  local mutation="$2"
  python3 -c "import json; p=json.load(open('$SAMPLE')); $mutation; json.dump(p, open('$TMP/$name.json','w'))"
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected invalid fixture to fail: $name" >&2
    exit 1
  fi
}

invalid_case duplicate_metric "p['metrics'].append(dict(p['metrics'][0]))"
invalid_case duplicate_event "p['events'].append(dict(p['events'][0]))"
invalid_case bad_north_star "p['north_star']['metric_id']='missing_metric'"
invalid_case no_dedupe "p['events'][0].pop('dedupe_key')"
invalid_case client_durable "p['events'][0]['source']='client'"
invalid_case forbidden_secret "p['events'][0]['properties'].append({'name':'api_key','type':'string','required':False,'classification':'sensitive','privacy_basis':'none','retention_days':1})"
invalid_case pii_without_policy "p['events'][0]['properties'].append({'name':'email','type':'string','required':False,'classification':'pii'})"
invalid_case unknown_experiment_metric "p['experiments'][0]['primary_metric']='missing_metric'"
invalid_case unknown_exposure_event "p['experiments'][0]['exposure_event']='missing_event'"
invalid_case nonguardrail_reference "p['experiments'][0]['guardrails']=['activation_rate']"

echo "product metrics fixtures passed"
