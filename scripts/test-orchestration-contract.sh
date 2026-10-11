#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-orchestration-contract.py"
S="$ROOT/templates/agentic/orchestration-contract.sample.json"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" >/dev/null
python3 - "$S" "$T/captured.json" <<'PY'
import json
import sys
d=json.load(open(sys.argv[1]))
d['receipt_kind']='captured_contract'
d['review']['approved']=True
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
mutate cycle 'd["delegations"].append({"from":"code_worker","to":"manager","task_id":"task_cycle","input_refs":["x"],"context_allowlist":["goal"],"authority_tools":["read"],"output_ref":"x","evidence_required":["x"],"approval_required":False})'
mutate authority_escalation 'd["delegations"][0]["authority_tools"].append("deploy")'
mutate undeclared_child_tool 'd["delegations"][1]["authority_tools"].remove("browser")'
mutate shared_write 'd["lanes"][2]["write"]=["artifacts/code"]'
mutate duplicate_lane_agent 'd["lanes"][2]["agent_id"]="code_worker"'
mutate unassigned_requirement 'd["agents"][0]["requirements"]=["req_code"]'
mutate overspend 'd["agents"][1]["budget"]["max_cost_usd"]=4.0'
mutate no_cancel 'd["failure_policy"]["cancel_descendants"]=False'
mutate sensitive_trace 'd["trace_policy"]["include_sensitive_data"]=True'
mutate missing_handoff_trace 'd["trace_policy"]["events"].remove("handoff")'
mutate self_review 'd["review"]["independent_reviewer"]=d["review"]["owner"]'
mutate illustrative_approval 'd["receipt_kind"]="illustrative_fixture"'
mutate no_independent_verify 'd["synthesis"]["independent_verification"]=False'
echo "orchestration contract fixtures passed"
