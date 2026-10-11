#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-browser-session.py"
S="$ROOT/templates/agentic/browser-session.sample.json"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" >/dev/null
cp -R "$ROOT/templates/agentic/browser-session-evidence" "$T/browser-session-evidence"
python3 - "$S" "$T/captured.json" <<'PY'
import json
import sys
d=json.load(open(sys.argv[1]))
d['receipt_kind']='captured_session'
d['review']['approved']=True
d['decision']={'outcome':'pass','reasons':['Captured read-only session matched policy.'],'unresolved_risks':[]}
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
mutate forged_artifact 'd["artifacts"][0]["sha256"]="0"*64'
mutate persistent_profile 'd["session"]["profile"]="daily-chrome"'
mutate shared_auth 'd["session"]["storage_state"]["shared_between_workers"]=True'
mutate logged_out_storage 'd["session"]["storage_state"].update(used=True,source="daily.json")'
mutate missing_query_guard 'd["policy"]["network"]["forbidden_query_keys"]=[]'
mutate permission_enabled 'd["policy"]["permissions"]["camera"]="allow"'
mutate missing_always_ask 'd["policy"]["actions"]["always_ask"].remove("payment")'
mutate unexpected_origin 'd["observations"]["navigations"][0]["url"]="https://example.invalid/"'
mutate secret_in_url 'd["observations"]["navigations"][0]["url"]="http://127.0.0.1:3000/?token=synthetic"'
mutate page_url_unapproved 'd["observations"]["navigations"][0].update(url="http://127.0.0.1:3000/other",source="page",public_indexed=False,user_approved=False)'
mutate egress_request 'd["observations"]["requests"][0]["url"]="https://example.invalid/collect"'
mutate sensitive_request 'd["observations"]["requests"][0]["sensitive_data"]=True'
mutate page_authorized_mutation 'd["policy"]["actions"]["allowed"].append("click_submit"); d["observations"]["actions"][0].update(kind="click_submit",mutation=True,source="page_content")'
mutate wrong_target_approval 'd["policy"]["actions"]["allowed"].append("click_submit"); d["policy"]["actions"]["mutations"]=[{"id":"approve_submit","kind":"click_submit","target":"safe-form","approved":True}]; d["observations"]["actions"][0].update(kind="click_submit",target="other-form",mutation=True,approval_id="approve_submit")'
mutate popup 'd["observations"]["popups"]=[{"url":"https://example.invalid","expected":False,"closed":False,"origin_allowed":False}]'
mutate download 'd["observations"]["transfers"]=[{"kind":"download","path":"payload.bin","expected_sha256":None,"quarantined":False,"executed":True,"approval_id":None}]'
mutate permission_prompt 'd["observations"]["permission_prompts"]=["notifications"]'
mutate injection_followed 'd["observations"]["injection"].update(encountered=True,followed=True,stopped=False)'
mutate injection_not_stopped 'd["observations"]["injection"].update(encountered=True,stopped=False)'
mutate incomplete_cleanup 'd["cleanup"]["context_closed"]=False'
mutate console_error_pass 'd["observations"]["console_errors"]=["uncaught"]'
mutate illustrative_pass 'd["receipt_kind"]="illustrative_fixture"'
echo "browser session fixtures passed"
