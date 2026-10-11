#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/run-browser-lanes.py"
VALIDATOR="$ROOT/scripts/validate-browser-lane-execution.py"
SAMPLE="$ROOT/templates/agentic/playwright-lane-plan.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin" "$TMP/.engineer/browser-runs"

python3 "$RUNNER" "$SAMPLE" --root "$ROOT" --print-commands >"$TMP/commands.json"
ln -s "$SAMPLE" "$TMP/plan-link.json"
if python3 "$RUNNER" "$TMP/plan-link.json" --root "$ROOT" --print-commands >/dev/null 2>&1; then
  echo "symlinked browser plan unexpectedly accepted" >&2
  exit 1
fi
python3 - "$TMP/commands.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d['ok'] and not d['executable']
assert [(x['kind'],x['phase']) for x in d['commands']]==[('public','parallel_read'),('quality','parallel_read')]
assert all(x['argv'][:4]==['pnpm','exec','playwright','test'] for x in d['commands'])
assert all(not x['credential_environment_names'] for x in d['commands'])
assert all(x['inherited_environment_allowlist']==['CI','LANG','LC_ALL','PATH'] for x in d['commands'])
PY
if python3 "$RUNNER" "$SAMPLE" --root "$ROOT" --execute >/dev/null 2>&1; then
  echo "illustrative browser plan unexpectedly executed" >&2; exit 1
fi

cat >"$TMP/bin/pnpm" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
[[ -z "${ENGINEER_SHOULD_NOT_LEAK:-}" ]] || { echo "unapproved environment leaked" >&2; exit 9; }
[[ "$HOME" == "$PWD/.engineer/browser-runs/captured-lanes/"*/home ]] || { echo "developer HOME leaked" >&2; exit 10; }
if [[ "$E2E_LANE" =~ ^(public|quality)$ ]]; then
  [[ -z "${E2E_EMAIL:-}${E2E_PASSWORD:-}" ]] || { echo "credentials leaked to public lane" >&2; exit 11; }
fi
mkdir -p "$PLAYWRIGHT_JSON_OUTPUT_DIR" "$E2E_OUTPUT_DIR"
if [[ "$E2E_LANE" == "auth-write" ]]; then
  test -f ".engineer/browser-runs/captured-lanes/public/results.json"
  test -f ".engineer/browser-runs/captured-lanes/quality/results.json"
else
  sleep 0.2
fi
printf '{"lane":"%s","status":"passed"}\n' "$E2E_LANE" >"$PLAYWRIGHT_JSON_OUTPUT_DIR/results.json"
SH
chmod +x "$TMP/bin/pnpm"

python3 - "$SAMPLE" "$TMP/plan.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d.update(run_kind='captured_run',run_id='captured-lanes',base_url='https://preview.example.test',app_root='.',output_root='.engineer/browser-runs/captured-lanes')
for lane in d['lanes']: lane['enabled']=lane['kind'] in {'public','quality','auth-write'}
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
if PATH="$TMP/bin:$PATH" E2E_EMAIL=fixture@example.test E2E_PASSWORD=fixture python3 "$RUNNER" "$TMP/plan.json" --root "$TMP" --execute >/dev/null 2>&1; then
  echo "write lane executed without mutation acknowledgement" >&2; exit 1
fi
PATH="$TMP/bin:$PATH" ENGINEER_SHOULD_NOT_LEAK=secret E2E_EMAIL=fixture@example.test E2E_PASSWORD=fixture \
  python3 "$RUNNER" "$TMP/plan.json" --root "$TMP" --execute --acknowledge-mutations >/dev/null
python3 "$VALIDATOR" "$TMP/.engineer/browser-runs/captured-lanes/execution.json" --root "$TMP" >/dev/null
ln -s "$TMP/.engineer/browser-runs/captured-lanes/execution.json" "$TMP/execution-link.json"
if python3 "$VALIDATOR" "$TMP/execution-link.json" --root "$TMP" >/dev/null 2>&1; then
  echo "symlinked browser execution receipt unexpectedly validated" >&2
  exit 1
fi
python3 - "$TMP/.engineer/browser-runs/captured-lanes/execution.json" <<'PY'
import json,sys
from datetime import datetime
d=json.load(open(sys.argv[1])); lanes={x['kind']:x for x in d['lanes']}
parse=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'))
assert d['decision']['outcome']=='pass' and d['decision']['receipt_compilation_required'] is True
assert parse(lanes['auth-write']['started_at']) >= max(parse(lanes[x]['ended_at']) for x in ('public','quality'))
assert all({a['kind'] for a in lane['artifacts']}=={'report','stdout','stderr'} for lane in lanes.values())
PY

python3 - "$TMP/.engineer/browser-runs/captured-lanes/execution.json" "$TMP/tampered.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d['lanes'][0]['command_sha256']='0'*64; json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
if python3 "$VALIDATOR" "$TMP/tampered.json" --root "$TMP" >/dev/null 2>&1; then
  echo "tampered browser execution unexpectedly validated" >&2; exit 1
fi

mutate_plan() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$RUNNER" "$TMP/$name.json" --root "$TMP" --print-commands >/dev/null 2>&1; then
    echo "expected browser plan rejection: $name" >&2; exit 1
  fi
}
mutate_plan production 'd["environment"]="production"'
mutate_plan query_url 'd["base_url"]="https://preview.example.test/?token=x"'
mutate_plan output_escape 'd["output_root"]="../outside"'
mutate_plan parallel_write 'd["lanes"][3]["workers"]=2'
mutate_plan duplicate_id 'd["lanes"][1]["id"]=d["lanes"][0]["id"]'

echo "browser lane execution fixtures passed"
