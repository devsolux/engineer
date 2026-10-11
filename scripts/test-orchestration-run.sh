#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-orchestration-run.py"
S="$ROOT/templates/agentic/orchestration-run.sample.json"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" >/dev/null
cp "$ROOT/templates/agentic/orchestration-contract.sample.json" "$T/orchestration-contract.sample.json"
cp -R "$ROOT/templates/agentic/orchestration-run-evidence" "$T/orchestration-run-evidence"
python3 - "$S" "$T/captured.json" <<'PY'
import json
import sys
d=json.load(open(sys.argv[1]))
d['receipt_kind']='captured_run'
d['review']['approved']=True
d['decision']={'outcome':'pass','reasons':['Captured run satisfied the bound contract.'],'unresolved_risks':[]}
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
python3 "$V" "$T/captured.json" >/dev/null
mutate() {
  local name="$1" expression="$2"
  python3 - "$T/captured.json" "$T/$name.json" "$expression" <<'PY'
import json
import sys
d=json.load(open(sys.argv[1]))
exec(sys.argv[3],{'d':d})
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$V" "$T/$name.json" >/dev/null 2>&1; then
    echo "expected rejection: $name" >&2
    exit 1
  fi
}
mutate forged_contract 'd["run"]["contract_sha256"]="0"*64'
mutate forged_artifact 'd["artifacts"][0]["sha256"]="0"*64'
mutate sensitive_trace 'd["trace"]["include_sensitive_data"]=True'
mutate incomplete_trace 'd["trace"]["complete"]=False'
mutate missing_worker 'd["workers"]=d["workers"][:-1]'
mutate unreleased_lease 'd["workers"][1]["lease_released"]=False'
mutate worker_overspend 'd["workers"][1]["cost_usd"]=2.0'
mutate success_without_artifact 'd["workers"][1]["output_artifact_id"]="art_ui"'
mutate undeclared_tool 'd["spans"][5]["tool"]="deploy"'
mutate undeclared_destination 'd["spans"][8]["destination"]="https://example.invalid"'
mutate cross_lane_write 'd["spans"][10]["write_lane"]="artifacts/code"'
mutate missing_approval 'd["spans"][8]["approval"]=None'
mutate broken_parent 'd["spans"][5]["parent_span_id"]="missing"'
mutate missing_handoff 'd["spans"]=[s for s in d["spans"] if s["span_id"]!="span_handoff_ui"]; [s.update(seq=i+1) for i,s in enumerate(d["spans"])]'
mutate wrong_join 'd["join"]["participants"]=["code_worker"]'
mutate missing_provenance 'd["synthesis"]["provenance"].pop("req_ui")'
mutate self_verification 'd["synthesis"]["verifier"]="manager"'
mutate self_review 'd["review"]["reviewer"]="manager"'
mutate infrastructure_pass 'd["run"]["infrastructure_errors"]=["trace exporter dropped spans"]'
mutate unresolved_pass 'd["decision"]["unresolved_risks"]=["worker state uncertain"]'
mutate illustrative_pass 'd["receipt_kind"]="illustrative_fixture"'
echo "orchestration run fixtures passed"
