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
echo "MCP session fixtures passed"
