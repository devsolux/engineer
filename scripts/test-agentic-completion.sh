#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-agentic-completion.py"
S="$ROOT/templates/agentic/completion-receipt.sample.json"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" --evidence-root "$ROOT" >/dev/null
mutate() {
  local name="$1" expression="$2"
  python3 - "$S" "$T/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]));exec(sys.argv[3],{'d':d});json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$V" "$T/$name.json" --evidence-root "$ROOT" >/dev/null 2>&1;then echo "expected rejection: $name" >&2;exit 1;fi
}
mutate contract_forgery 'd["contract"]["sha256"]="0"*64'
mutate contract_escape 'd["contract"]["path"]="../contract.json"'
mutate trajectory_forgery 'd["trajectory"]["sha256"]="0"*64'
mutate artifact_root_escape 'd["artifact_root"]="../evidence"'
mutate artifact_forgery 'd["artifacts"][0]["sha256"]="0"*64'
mutate missing_artifact 'd["artifacts"]=[]'
mutate missing_acceptance 'd["acceptance"].pop()'
mutate duplicate_acceptance 'd["acceptance"].append(dict(d["acceptance"][0]))'
mutate criterion_forgery 'd["acceptance"][0]["criterion_sha256"]="0"*64'
mutate requirement_drift 'd["acceptance"][0]["requirement_ids"]=["req_stop"]'
mutate oracle_count_forgery 'd["acceptance"][0]["oracle_count"]=2'
mutate oracle_false 'd["acceptance"][0]["oracle_passed"]=False'
mutate self_review 'd["review"]["checker"]=d["review"]["maker"]'
mutate no_scope_review 'd["review"]["scope_diff_reviewed"]=False'
mutate no_oracle_review 'd["review"]["oracle_sufficiency_reviewed"]=False'
mutate illustrative_complete 'd["review"]["approved"]=True;d["decision"]={"outcome":"complete","reasons":["fixture"],"unresolved_risks":[]}'
mutate malformed_review 'd["review"]=[]'
mutate malformed_decision 'd["decision"]=[]'
evidence_mutate() {
  local name="$1" expression="$2"
  local D="$T/$name";mkdir -p "$D/templates/agentic/completion-evidence"
  cp "$ROOT/templates/agentic/execution-contract.sample.json" "$D/templates/agentic/execution-contract.sample.json"
  cp "$ROOT/templates/agentic/trajectory.sample.json" "$D/templates/agentic/trajectory.sample.json"
  python3 - "$S" "$ROOT/templates/agentic/completion-evidence/verification.json" "$D/receipt.json" "$D/templates/agentic/completion-evidence/verification.json" "$expression" <<'PY'
import hashlib,json,sys
r=json.load(open(sys.argv[1]));d=json.load(open(sys.argv[2]));exec(sys.argv[5],{'d':d});raw=(json.dumps(d,indent=2)+'\n').encode();open(sys.argv[4],'wb').write(raw);r['artifacts'][0]['sha256']=hashlib.sha256(raw).hexdigest();json.dump(r,open(sys.argv[3],'w'),indent=2)
PY
  if python3 "$V" "$D/receipt.json" --evidence-root "$D" >/dev/null 2>&1;then echo "expected rejection: $name" >&2;exit 1;fi
}
evidence_mutate resume_status 'd["acceptance"]["ac_resume"]["status"]="failed"'
evidence_mutate resume_wrong_step 'd["acceptance"]["ac_resume"]["resumed_from_step"]="step_stop"'
evidence_mutate repeated_action 'd["acceptance"]["ac_resume"]["duplicate_actions"]=1'
evidence_mutate wrong_no_progress_count 'd["acceptance"]["ac_stop"]["unchanged_observations"]=3'
evidence_mutate wrong_stop_reason 'd["acceptance"]["ac_stop"]["stop_reason"]="model_said_done"'
evidence_mutate missing_command 'd["commands"]=[]'
evidence_mutate extra_command 'd["commands"].append(dict(d["commands"][0],command="echo pass"))'
evidence_mutate failed_command 'd["commands"][0]["exit_code"]=1'
evidence_mutate timed_out_command 'd["commands"][0]["timed_out"]=True'
evidence_mutate command_time_reversal 'd["commands"][0]["completed_at"]="2026-07-15T05:00:00Z"'
evidence_mutate evidence_contract_swap 'd["contract_sha256"]="0"*64'
evidence_mutate evidence_trajectory_swap 'd["trajectory_sha256"]="0"*64'
evidence_mutate invalid_revision 'd["revision_after_sha256"]="main"'
evidence_mutate evidence_acceptance_removed 'd["acceptance"].pop("ac_stop")'

TR="$T/trusted";mkdir -p "$TR/templates/agentic/completion-evidence"
cp "$ROOT/templates/agentic/execution-contract.sample.json" "$TR/templates/agentic/execution-contract.sample.json"
cp "$ROOT/templates/agentic/trajectory.sample.json" "$TR/templates/agentic/trajectory.sample.json"
python3 - "$S" "$ROOT/templates/agentic/completion-evidence/verification.json" "$TR/receipt.json" "$TR/templates/agentic/completion-evidence/verification.json" <<'PY'
import hashlib,json,sys
r=json.load(open(sys.argv[1]));d=json.load(open(sys.argv[2]));d['capture_kind']='captured_run';raw=(json.dumps(d,indent=2)+'\n').encode();open(sys.argv[4],'wb').write(raw);r['artifacts'][0]['sha256']=hashlib.sha256(raw).hexdigest();r['receipt_kind']='captured_completion';r['review']['approved']=True;r['decision']={'outcome':'complete','reasons':['Captured evidence satisfies every contract oracle.'],'unresolved_risks':[]};json.dump(r,open(sys.argv[3],'w'),indent=2)
PY
python3 "$V" "$TR/receipt.json" --evidence-root "$TR" >/dev/null
echo "Agentic completion fixtures passed"
