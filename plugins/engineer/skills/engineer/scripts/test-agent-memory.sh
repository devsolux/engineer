#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-agent-memory.py"
S="$ROOT/templates/agentic/agent-memory.sample.json"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" >/dev/null
python3 - "$S" "$T/captured.json" <<'PY'
import json
import sys
d=json.load(open(sys.argv[1]))
d['receipt_kind']='captured_review'
d['review']['approved']=True
d['decision']={'outcome':'admit','reasons':['Captured review accepted the verified preference and quarantined hostile content.'],'unresolved_risks':[]}
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
  if python3 "$V" "$T/$name.json" >/dev/null 2>&1; then echo "expected rejection: $name" >&2; exit 1; fi
}
mutate raw_secret 'd["entries"][0]["sensitivity"]="secret"'
mutate grants_authority 'd["entries"][0]["authority"]=True'
mutate untrusted_active 'd["entries"][1].update(status="active"); d["lifecycle"][1]["operation"]="admit"'
mutate cross_tenant 'd["retrievals"][0]["tenant_id"]="other_tenant"'
mutate quarantined_retrieval 'd["retrievals"][0]["entry_ids"]=["mem_untrusted_note"]'
mutate purpose_mismatch 'd["retrievals"][0]["purpose"]="code_assistance"'
mutate scope_mismatch 'd["retrievals"][0]["scope"]="project"'
mutate rank_before_access 'd["retrievals"][0]["ranking_after_access"]=False'
mutate missing_provenance 'd["retrievals"][0]["provenance_included"]=False'
mutate over_budget 'd["retrievals"][0]["token_limit"]=2001'
mutate duplicate_active_key 'x=dict(d["entries"][0]); x["id"]="mem_pref_theme_2"; x["content_sha256"]="d"*64; d["entries"].append(x); y=dict(d["lifecycle"][0]); y["entry_id"]=x["id"]; y["audit_event"]="fixture-duplicate"; d["lifecycle"].append(y)'
mutate unsafe_global 'd["entries"][0]["scope"]="global"; d["retrievals"][0]["scope"]="global"'
mutate pii_without_consent 'd["entries"][0]["sensitivity"]="pii"; d["entries"][0]["consent"].update(required=False,obtained=False,at=None)'
mutate overlong_expiry 'd["entries"][0]["expires_at"]="2028-07-15T00:00:00Z"'
mutate incomplete_delete 'd["entries"][0]["status"]="tombstone"; d["lifecycle"][0]["operation"]="delete"'
mutate lifecycle_mismatch 'd["lifecycle"][0]["operation"]="quarantine"'
mutate missing_lifecycle 'd["lifecycle"].pop()'
mutate missing_resurrection_test 'd["tests"]["deletion_resurrection"]=False'
mutate self_review 'd["review"]["independent_reviewer"]=d["review"]["owner"]'
mutate stale_review 'd["review"]["review_after"]="2026-07-14T00:00:00Z"'
mutate illustrative_admit 'd["receipt_kind"]="illustrative_fixture"'
mutate unresolved_admit 'd["decision"]["unresolved_risks"]=["unknown replica"]'
mutate unknown_reference 'd["entries"][0]["contradicts"]=["missing"]'
mutate raw_content_field 'd["entries"][0]["content"]="do not store raw receipt content"'
echo "agent memory fixtures passed"
