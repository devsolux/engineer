#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$ROOT/scripts/validate-mcp-session.py"
S="$ROOT/templates/agentic/mcp-session.sample.json"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
python3 "$V" "$S" --evidence-root "$ROOT" >/dev/null
python3 - "$S" "$T/captured.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d['receipt_kind']='captured_session'; d['review']['approved']=True
d['decision']={'outcome':'trust','reasons':['Captured isolated MCP session matched the reviewed policy.'],'unresolved_risks':[]}
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
python3 "$V" "$T/captured.json" --evidence-root "$ROOT" >/dev/null
mutate() {
  local name="$1" expression="$2"
  python3 - "$T/captured.json" "$T/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$V" "$T/$name.json" --evidence-root "$ROOT" >/dev/null 2>&1; then echo "expected rejection: $name" >&2; exit 1; fi
}
mutate mutable_revision 'd["server"]["revision_sha256"]="main"'
mutate unsupported_protocol 'd["server"]["protocol_version"]="2099-01-01"'
mutate stateless_2026_07_28 'd["server"]["protocol_version"]="2026-07-28"'
(python3 "$V" "$T/stateless_2026_07_28.json" --evidence-root "$ROOT" --json 2>/dev/null || true) | grep -q 'rejected, never downgraded' || { echo "a 2025-11-25 capture relabeled 2026-07-28 must be rejected, never downgraded" >&2; exit 1; }
mutate no_sandbox 'd["server"]["sandboxed"]=False'
mutate insecure_endpoint 'd["server"]["endpoint"]="http://mcp.example.test/mcp"'
mutate no_resource_metadata 'd["authorization"]["protected_resource_metadata"]=None'
mutate no_401_discovery 'd["authorization"]["protected_resource_401_discovery"]=False'
mutate no_path_discovery 'd["authorization"]["protected_resource_path_discovery"]=False'
mutate no_root_fallback 'd["authorization"]["protected_resource_root_fallback"]=False'
mutate no_oidc_discovery 'd["authorization"]["oidc_metadata_discovery"]=False'
mutate issuer_not_allowed 'd["authorization"]["selected_issuer_allowed"]=False'
mutate client_metadata_http 'd["authorization"]["client_id"]="http://client.example.test/metadata.json"'
mutate client_metadata_ssrf 'd["authorization"]["client_metadata_ssrf_mitigated"]=False'
mutate localhost_client_spoof 'd["authorization"]["localhost_redirect_impersonation_mitigated"]=False'
mutate wrong_resource 'd["authorization"]["resource_indicator"]="https://other.example.test/mcp"'
mutate no_pkce 'd["authorization"]["pkce_s256"]=False'
mutate scope_challenge_ignored 'd["authorization"]["scope_challenge_parsed"]=False'
mutate no_step_up 'd["authorization"]["step_up_supported"]=False'
mutate token_query 'd["authorization"]["token_in_query"]=True'
mutate wrong_audience 'd["authorization"]["audience_validated"]=False'
mutate token_passthrough 'd["authorization"]["token_passthrough"]=True'
mutate wildcard_scope 'd["authorization"]["requested_scopes"].append("*")'
mutate unconsented_root 'd["capabilities"]["roots"]["consented"]=False'
mutate root_traversal 'd["capabilities"]["roots"]["uris"]=["file:///fixture/../secret"]'
mutate sampling_no_review 'd["capabilities"]["sampling"]["human_review_request"]=False'
mutate elicitation_form_secret 'd["capabilities"]["elicitation"]["form"]["sensitive_requested"]=True'
mutate elicitation_form_link 'd["capabilities"]["elicitation"]["form"]["clickable_urls"]=True'
mutate elicitation_url_auto_open 'd["capabilities"]["elicitation"]["url"]["auto_open"]=True'
mutate elicitation_url_prefetch 'd["capabilities"]["elicitation"]["url"]["auto_fetch"]=True'
mutate elicitation_url_sensitive_data 'd["capabilities"]["elicitation"]["url"]["sensitive_url_data"]=True'
mutate elicitation_url_preauthenticated 'd["capabilities"]["elicitation"]["url"]["preauthenticated_url"]=True'
mutate elicitation_url_observed 'd["capabilities"]["elicitation"]["url"]["client_content_access"]=True'
mutate elicitation_url_no_consent 'd["capabilities"]["elicitation"]["url"]["explicit_consent"]=False'
mutate elicitation_url_hidden 'd["capabilities"]["elicitation"]["url"]["full_url_shown"]=False'
mutate elicitation_url_spoofing 'd["capabilities"]["elicitation"]["url"]["domain_highlighted"]=False'
mutate elicitation_url_wrong_user 'd["capabilities"]["elicitation"]["url"]["user_binding_verified"]=False'
mutate elicitation_url_unknown_completion 'd["capabilities"]["elicitation"]["url"]["completion_ids_validated"]=False'
mutate elicitation_url_no_manual_resume 'd["capabilities"]["elicitation"]["url"]["manual_resume_supported"]=False'
mutate elicitation_mode_mismatch 'd["capabilities"]["elicitation"]["modes"]=["form"]'
mutate schema_drift 'd["tools"][0]["input_schema_sha256"]="changed"'
mutate tool_scope_escalation 'd["tools"][0]["scopes"]=["admin:all"]'
mutate egress_escape 'd["tools"][0]["destinations"]=["https://evil.example.test"]'
mutate mutation_no_confirmation 'd["tools"][1]["confirmation_required"]=False'
mutate mutation_no_idempotency 'd["calls"][1]["idempotency_key"]=None'
mutate cross_tenant_root 'd["calls"][0]["root_uri"]="file:///other"'
mutate call_scope_escalation 'd["calls"][0]["scopes"].append("admin:all")'
mutate sensitive_result 'd["calls"][0]["sensitive_output"]=True'
mutate timeout_overrun 'd["calls"][0]["completed_at"]="2026-07-15T04:00:10Z"'
mutate missing_regression 'd["tests"]["prompt_injection"]=False'
mutate self_review 'd["review"]["independent_reviewer"]=d["review"]["owner"]'
mutate illustrative_trust 'd["receipt_kind"]="illustrative_fixture"'
mutate unresolved_trust 'd["decision"]["unresolved_risks"]=["unknown egress"]'
mutate hidden_field 'd["tools"][0]["hidden_command"]="shell"'
mutate snapshot_escape 'd["server"]["tools_snapshot_path"]="../tools-list.json"'
mutate forged_snapshot_hash 'd["server"]["tools_snapshot_sha256"]="0"*64'
mutate manifest_escape 'd["server"]["capture_manifest_path"]="../capture-manifest.json"'
mutate manifest_forgery 'd["server"]["capture_manifest_sha256"]="0"*64'
snapshot_mutate() {
  local name="$1" expression="$2"
  mkdir -p "$T/$name/evidence"
  python3 - "$S" "$ROOT/templates/agentic/mcp-evidence/tools-list.json" "$T/$name/receipt.json" "$T/$name/evidence/tools-list.json" "$expression" <<'PY'
import hashlib,json,sys
receipt=json.load(open(sys.argv[1])); snapshot=json.load(open(sys.argv[2])); exec(sys.argv[5],{'d':snapshot})
raw=(json.dumps(snapshot,indent=2)+'\n').encode(); open(sys.argv[4],'wb').write(raw)
receipt['server']['tools_snapshot_path']='evidence/tools-list.json'; receipt['server']['tools_snapshot_sha256']=hashlib.sha256(raw).hexdigest()
receipt['receipt_kind']='captured_session'; receipt['review']['approved']=True; receipt['decision']={'outcome':'trust','reasons':['fixture'],'unresolved_risks':[]}
json.dump(receipt,open(sys.argv[3],'w'),indent=2)
PY
  if python3 "$V" "$T/$name/receipt.json" --evidence-root "$T/$name" >/dev/null 2>&1; then echo "expected rejection: $name" >&2; exit 1; fi
}
snapshot_mutate injected_tool 'd["tools"].append({"name":"hidden_admin","description":"Hidden.","inputSchema":{"type":"object","properties":{},"required":[],"additionalProperties":False},"outputSchema":{"type":"object","properties":{},"required":[],"additionalProperties":False}})'
snapshot_mutate removed_tool 'd["tools"].pop()'
snapshot_mutate changed_description 'd["tools"][0]["description"]="Changed after review."'
snapshot_mutate changed_input_schema 'd["tools"][0]["inputSchema"]["properties"]["tenant"]={"type":"string"}'
snapshot_mutate unsafe_output_schema 'd["tools"][0]["outputSchema"]["additionalProperties"]=True'

# 2026-07-28 stateless receipts bind a stateless capture and acknowledge deprecated-feature exposure.
C="$ROOT/scripts/compile-mcp-transcript.py"
S2="$ROOT/templates/agentic/mcp-session-2026-07-28.sample.json"
python3 "$V" "$S2" --evidence-root "$ROOT" >/dev/null
python3 - "$S2" "$T/stateless-captured.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d['receipt_kind']='captured_session'; d['review']['approved']=True
d['decision']={'outcome':'trust','reasons':['Captured isolated stateless MCP session matched the reviewed policy.'],'unresolved_risks':[]}
json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
python3 "$V" "$T/stateless-captured.json" --evidence-root "$ROOT" >/dev/null
verdict() {
  local name="$1" receipt="$2" root="$3" outcome="$4" expected="$5" got=reject
  if python3 "$V" "$receipt" --evidence-root "$root" --json >"$T/$name.out" 2>&1; then got=accept; fi
  [[ "$got" == "$outcome" ]] || { echo "expected $outcome: $name" >&2; cat "$T/$name.out" >&2; exit 1; }
  [[ -z "$expected" ]] || grep -q -- "$expected" "$T/$name.out" || { echo "wrong verdict reason: $name" >&2; cat "$T/$name.out" >&2; exit 1; }
}
stateless_receipt() {
  local name="$1" expression="$2" outcome="$3" expected="${4:-}"
  python3 - "$T/stateless-captured.json" "$T/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  verdict "$name" "$T/$name.json" "$ROOT" "$outcome" "$expected"
}
# Recompile a mutated stateless transcript into an isolated root and rebind the receipt to it.
stateless_capture() {
  local name="$1" transcript_expr="$2" receipt_expr="$3" outcome="$4" expected="${5:-}"
  mkdir -p "$T/$name"
  python3 - "$ROOT/templates/agentic/mcp-evidence-2026-07-28/transcript.jsonl" "$T/$name/transcript.jsonl" "$transcript_expr" <<'PY'
import json,sys
d=[json.loads(x) for x in open(sys.argv[1]) if x.strip()];CAPS='io.modelcontextprotocol/clientCapabilities'
def meta(i):return d[i]['message']['params']['_meta']
def renumber():[x.__setitem__('seq',i+1) for i,x in enumerate(d)]
exec(sys.argv[3],{'d':d,'meta':meta,'renumber':renumber,'CAPS':CAPS})
open(sys.argv[2],'w').write(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in d))
PY
  python3 "$C" "$T/$name/transcript.jsonl" --output-dir "$T/$name/evidence" >/dev/null
  python3 - "$T/stateless-captured.json" "$T/$name" "$receipt_expr" <<'PY'
import hashlib,json,sys
d=json.load(open(sys.argv[1]));root=sys.argv[2]
def sha(p):return hashlib.sha256(open(f'{root}/{p}','rb').read()).hexdigest()
d['server'].update({'tools_snapshot_path':'evidence/tools-list.json','tools_snapshot_sha256':sha('evidence/tools-list.json'),'capture_manifest_path':'evidence/capture-manifest.json','capture_manifest_sha256':sha('evidence/capture-manifest.json')})
exec(sys.argv[3],{'d':d});json.dump(d,open(f'{root}/receipt.json','w'),indent=2)
PY
  verdict "$name" "$T/$name/receipt.json" "$T/$name" "$outcome" "$expected"
}
stateless_receipt stateless_missing_flag_list 'd["capabilities"].pop("deprecated_feature_exposure")' reject 'capability negotiation invalid'
stateless_receipt stateless_unknown_flag 'd["capabilities"]["deprecated_feature_exposure"]=["telepathy"]' reject 'unique known deprecated features'
stateless_receipt stateless_duplicate_flag 'd["capabilities"]["deprecated_feature_exposure"]=["logging","logging"]' reject 'unique known deprecated features'
stateless_receipt stateless_overflagged 'd["capabilities"]["deprecated_feature_exposure"]=["sampling"]' reject 'deprecated_feature_exposure flags differ'
stateless_receipt dynamic_registration_unflagged 'd["authorization"]["client_registration_mode"]="dynamic"' reject 'deprecated_feature_exposure flags differ'
stateless_receipt dynamic_registration_flagged 'd["authorization"]["client_registration_mode"]="dynamic";d["capabilities"]["deprecated_feature_exposure"]=["dynamic_client_registration"]' accept
stateless_receipt roots_negotiated_unflagged 'd["capabilities"]["negotiated"].append("roots");d["capabilities"]["roots"]={"enabled":True,"uris":["file:///fixture/workspace"],"consented":True,"path_validation":True,"list_changes":True}' reject 'deprecated_feature_exposure flags differ'
stateless_receipt stateless_root_without_roots 'd["calls"][0]["root_uri"]="file:///fixture/workspace"' reject 'destination or root outside policy'
stateless_receipt stateless_relabeled_legacy 'd["server"]["protocol_version"]="2025-11-25"' reject 'rejected, never downgraded'
stateless_receipt stateless_illustrative_trust 'd["receipt_kind"]="illustrative_fixture"' reject 'trust requires captured approved session'
stateless_capture stateless_rebind_baseline 'pass' 'pass' accept
stateless_capture logging_level_unflagged 'meta(4)["io.modelcontextprotocol/logLevel"]="warning"' 'pass' reject 'deprecated_feature_exposure flags differ from exposed deprecated features: logging'
stateless_capture logging_level_flagged 'meta(4)["io.modelcontextprotocol/logLevel"]="warning"' 'd["capabilities"]["deprecated_feature_exposure"]=["logging"]' accept
stateless_capture sampling_capability_unflagged 'meta(2)[CAPS]["sampling"]={}' 'pass' reject 'deprecated_feature_exposure flags differ from exposed deprecated features: sampling'
stateless_capture server_logging_unflagged 'd[1]["message"]["result"]["capabilities"]["logging"]={}' 'pass' reject 'deprecated_feature_exposure'
stateless_capture without_discover 'del d[0:2];renumber()' 'pass' reject 'stateless capture lacks server/discover'
stateless_capture server_extension 'd[1]["message"]["result"]["capabilities"]["extensions"]={"io.modelcontextprotocol/ui":{}}' 'pass' reject 'server advertises extensions this receipt cannot review: io.modelcontextprotocol/ui'
stateless_capture client_capability_drift '[meta(i)[CAPS].pop("elicitation") for i in range(0,len(d),2)]' 'pass' reject 'client capabilities differ from transcript compilation'
echo "MCP session fixtures passed"
