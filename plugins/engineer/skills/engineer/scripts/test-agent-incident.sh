#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-agent-incident.py"
SAMPLE="$ROOT/templates/agentic/agent-incident.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$SAMPLE" >/dev/null
cp -R "$ROOT/templates/agentic/incident-evidence" "$TMP/incident-evidence"
python3 - "$SAMPLE" "$TMP/closed.json" <<'PY'
import json, sys
d=json.load(open(sys.argv[1])); d['receipt_kind']='captured_incident'; d['incident']['status']='closed'
d['decision'].update(outcome='close', unresolved_risks=[], closed_at='2026-07-15T03:00:00+00:00')
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
python3 "$VALIDATOR" "$TMP/closed.json" >/dev/null

mutate() {
  local name="$1" expression="$2"
  python3 - "$TMP/closed.json" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then echo "expected rejection: $name" >&2; exit 1; fi
}
mutate forged_evidence 'd["evidence"]["artifacts"][0]["sha256"]="0"*64'
mutate cleanup_before_capture 'd["eradication"]["evidence_preserved_before_cleanup"]=False'
mutate missing_revoke 'd["containment"]=[x for x in d["containment"] if x["action"]!="revoke_credentials"]'
mutate raw_secret 'd["eradication"]["actions"].append("token=not-a-real-secret")'
mutate unassessed_blast 'd["blast_radius"]=d["blast_radius"][:-1]'
mutate poisoned_checkpoint 'd["recovery"]["reused_contaminated_state"]=True'
mutate new_indicator 'd["recovery"]["new_indicators"]=["unexpected egress"]'
mutate no_regression 'd["regression"]["passed"]=False'
mutate self_review 'd["roles"]["evidence_reviewer"]=d["roles"]["incident_commander"]'
mutate illustrative_close 'd["receipt_kind"]="illustrative_fixture"'
mutate unresolved_close 'd["decision"]["unresolved_risks"]=["scope uncertain"]'
echo "agent incident fixtures passed"
