#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-coordination-envelope.py"
S="$ROOT/templates/agentic/coordination-envelope.sample.json"
A="$ROOT/templates/agentic/coordination-evidence"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" --root "$ROOT" --artifact-root "$A" >/dev/null
mkdir -p "$T/root"
python3 - "$S" "$ROOT/templates/agentic/orchestration-contract.sample.json" "$T/root/orchestration.json" "$T/captured.json" <<'PY'
import hashlib
import json
import sys
d=json.load(open(sys.argv[1]))
c=json.load(open(sys.argv[2]))
c['receipt_kind']='captured_contract'
c['review']['approved']=True
raw=(json.dumps(c,indent=2)+'\n').encode()
open(sys.argv[3],'wb').write(raw)
d['contract']['path']='orchestration.json'
d['contract']['sha256']=hashlib.sha256(raw).hexdigest()
d['receipt_kind']='captured_delivery'
d['receiver']['outcome']='accepted'
d['ack']['status']='accepted'
d['review']['approved']=True
d['decision']={'outcome':'accept','reasons':['Captured pointer matched the approved delegation and local artifact.'],'unresolved_risks':[]}
json.dump(d,open(sys.argv[4],'w'),indent=2)
PY
python3 "$V" "$T/captured.json" --root "$T/root" --artifact-root "$A" >/dev/null
mutate() {
  local name="$1" expression="$2"
  python3 - "$T/captured.json" "$T/$name.json" "$expression" <<'PY'
import json
import sys
d=json.load(open(sys.argv[1]))
exec(sys.argv[3],{'d':d})
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$V" "$T/$name.json" --root "$T/root" --artifact-root "$A" >/dev/null 2>&1; then echo "expected rejection: $name" >&2; exit 1; fi
}
mutate sensitive_payload 'd["message"]["contains_sensitive_data"]=True'
mutate instruction_payload 'd["message"]["contains_instructions"]=True'
mutate authority_payload 'd["message"]["grants_authority"]=True'
mutate oversized 'd["message"]["payload_bytes"]=2001'
mutate broadcast 'd["transport"]["delivery_scope"]="broadcast"'
mutate invented_quota 'd["message"]["quota_signal"]["used_for_scheduling_only"]=False'
mutate forged_contract 'd["contract"]["sha256"]="0"*64'
mutate wrong_contract_id 'd["contract"]["id"]="other_goal"'
mutate unknown_task 'd["contract"]["task_id"]="unknown_task"'
mutate invented_schema 'd["pointer"]["schema"]="looks-valid-v1"'
mutate spoofed_sender 'd["message"]["from"]="ui_worker"'
mutate wrong_receiver 'd["contract"]["declared_receiver"]="ui_worker"'
mutate wrong_output 'd["contract"]["output_ref"]="artifacts/ui/result.json"'
mutate path_escape 'd["pointer"]["artifact_path"]="../result.json"'
mutate forged_artifact 'd["pointer"]["sha256"]="0"*64; d["ack"]["artifact_sha256"]="0"*64'
mutate executable 'd["pointer"]["executable"]=True'
mutate secret_pointer 'd["pointer"]["sensitivity"]="secret"'
mutate expired 'd["pointer"]["expires_at"]="2026-07-15T03:00:30Z"'
mutate replayed 'd["receiver"]["replayed"]=True'
mutate executed_message 'd["receiver"]["executed_from_message"]=True'
mutate persisted_memory 'd["receiver"]["persisted_as_memory"]=True'
mutate skipped_digest 'd["receiver"]["digest_verified"]=False'
mutate bad_ack 'd["ack"]["status"]="quarantined"'
mutate ack_before_receive 'd["ack"]["at"]="2026-07-15T03:00:30Z"'
mutate review_before_ack 'd["review"]["reviewed_at"]="2026-07-15T03:01:30Z"'
mutate future_quota 'd["message"]["quota_signal"]["observed_at"]="2026-07-15T03:00:30Z"'
mutate self_review 'd["review"]["independent_reviewer"]=d["review"]["owner"]'
mutate illustrative_accept 'd["receipt_kind"]="illustrative_fixture"'
mutate unresolved_accept 'd["decision"]["unresolved_risks"]=["delivery identity unauthenticated"]'
mutate unapproved_contract 'd["contract"]["path"]="missing.json"'
mutate extra_command 'd["message"]["command"]="deploy"'
python3 - "$T/root/orchestration.json" "$T/root/invalid-contract.json" "$T/captured.json" "$T/invalid-contract-receipt.json" <<'PY'
import hashlib,json,sys
c=json.load(open(sys.argv[1])); c['limits']['max_agents']=1
raw=(json.dumps(c,indent=2)+'\n').encode(); open(sys.argv[2],'wb').write(raw)
d=json.load(open(sys.argv[3])); d['contract']['path']='invalid-contract.json'; d['contract']['sha256']=hashlib.sha256(raw).hexdigest()
json.dump(d,open(sys.argv[4],'w'),indent=2)
PY
if python3 "$V" "$T/invalid-contract-receipt.json" --root "$T/root" --artifact-root "$A" >/dev/null 2>&1; then echo "expected rejection: invalid_contract_semantics" >&2; exit 1; fi
mkdir -p "$T/artifacts/artifacts/code"
python3 - "$T/captured.json" "$T/artifacts/artifacts/code/result.json" "$T/invalid-artifact-receipt.json" <<'PY'
import hashlib,json,sys
raw=b'{"findings": []}\n'; open(sys.argv[2],'wb').write(raw)
d=json.load(open(sys.argv[1])); h=hashlib.sha256(raw).hexdigest(); d['pointer']['sha256']=h; d['ack']['artifact_sha256']=h
json.dump(d,open(sys.argv[3],'w'),indent=2)
PY
if python3 "$V" "$T/invalid-artifact-receipt.json" --root "$T/root" --artifact-root "$T/artifacts" >/dev/null 2>&1; then echo "expected rejection: artifact_schema_missing_required" >&2; exit 1; fi
echo "coordination envelope fixtures passed"
