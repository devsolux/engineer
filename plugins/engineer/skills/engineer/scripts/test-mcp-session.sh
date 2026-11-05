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
def canonical(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rebind():
    captured={x['name']:x for x in json.load(open(f'{root}/evidence/tools-list.json'))['tools']}
    for t in d['tools']:
        c=captured[t['name']];t['input_schema_sha256']=canonical(c['inputSchema'])
        t['description_sha256']=hashlib.sha256(c['description'].encode()).hexdigest() if 'description' in c else None
        t['output_schema_sha256']=canonical(c['outputSchema']) if 'outputSchema' in c else None
exec(sys.argv[3],{'d':d,'rebind':rebind});json.dump(d,open(f'{root}/receipt.json','w'),indent=2)
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

# Tool definitions end to end: a spec-complete tool is admitted, and the receipt must stay honest about it.
GET='d[3]["message"]["result"]["tools"][0]'
NOTE='d[5]["message"]["result"]["tools"][0]'
stateless_capture tool_full_metadata "$GET.update(title=\"Get order\",annotations={\"title\":\"Get order\",\"readOnlyHint\":True,\"openWorldHint\":False},icons=[{\"src\":\"https://mcp.example.test/icon.png\",\"mimeType\":\"image/png\",\"sizes\":[\"48x48\"],\"theme\":\"dark\"}],_meta={\"example.test/category\":\"orders\"})" 'pass' accept
stateless_capture search_notes_tool "d[5][\"message\"][\"result\"][\"tools\"].append({\"name\":\"search_notes\",\"title\":\"Search notes\",\"description\":\"Search the caller's notes.\",\"annotations\":{\"readOnlyHint\":True},\"inputSchema\":{\"type\":\"object\",\"properties\":{\"query\":{\"type\":\"string\"},\"page_token\":{\"type\":\"string\"},\"max_tokens\":{\"type\":\"integer\"}},\"required\":[\"query\"],\"additionalProperties\":False}})" 'd["tools"].append({**d["tools"][0],"name":"search_notes","output_validated":False});rebind()' accept
stateless_capture tool_no_output_schema "$GET.pop(\"outputSchema\")" 'd["tools"][0]["output_validated"]=False;rebind()' accept
stateless_capture tool_no_description "$GET.pop(\"description\")" 'rebind()' accept
stateless_capture output_claim_without_schema "$GET.pop(\"outputSchema\")" 'rebind()' reject 'tool get_order claims output validation without an outputSchema'
stateless_capture stale_output_digest "$GET.pop(\"outputSchema\")" 'd["tools"][0]["output_validated"]=False' reject 'tool get_order metadata differs from captured snapshot'
stateless_receipt dropped_output_digest 'd["tools"][0]["output_schema_sha256"]=None' reject 'tool get_order metadata differs from captured snapshot'
stateless_receipt dropped_description_digest 'd["tools"][0]["description_sha256"]=None' reject 'tool get_order metadata differs from captured snapshot'
stateless_receipt dropped_input_digest 'd["tools"][0]["input_schema_sha256"]=None' reject 'tool 0 identity or bounds invalid'
stateless_capture hidden_tool_key "$GET.update(hidden_command=\"shell\")" 'pass' reject 'unreviewed keys for this revision: hidden_command'
stateless_capture readonly_hint_on_write "$NOTE.update(annotations={\"readOnlyHint\":True})" 'pass' reject 'tool update_order_note annotations contradict the reviewed risk'
stateless_capture readonly_hint_on_network "$NOTE.update(annotations={\"readOnlyHint\":True})" 'd["tools"][1]["risk"]="network"' accept
stateless_capture destructive_hint_on_read "$GET.update(annotations={\"destructiveHint\":True})" 'pass' reject 'tool get_order annotations contradict the reviewed risk'
stateless_capture destructive_hint_ignored_when_read_only "$GET.update(annotations={\"readOnlyHint\":True,\"destructiveHint\":True})" 'pass' accept
stateless_capture not_read_only_on_read "$GET.update(annotations={\"readOnlyHint\":False})" 'pass' reject 'tool get_order annotations contradict the reviewed risk'
stateless_capture header_mirror "$GET[\"inputSchema\"][\"properties\"][\"order_id\"][\"x-mcp-header\"]=\"Order\"" 'rebind()' accept
stateless_capture header_on_number "$GET[\"inputSchema\"][\"properties\"][\"order_id\"].update({\"x-mcp-header\":\"Order\",\"type\":\"number\"})" 'rebind()' reject 'x-mcp-header breaks the Streamable HTTP rules'

# Tool shape per revision: each row is one spec rule, read from that revision's schema.
python3 - "$V" <<'PY'
import importlib.util,sys
spec=importlib.util.spec_from_file_location('validator',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
R06,R25,R26='2025-06-18','2025-11-25','2026-07-28'
OPEN={'type':'object'};NONE={'type':'object','additionalProperties':False}
CLOSED={'type':'object','properties':{'q':{'type':'string'}},'required':['q'],'additionalProperties':False}
def tool(**k):return {'name':'search_notes','inputSchema':CLOSED,**k}
def prop(**k):return {'type':'object','properties':{'q':{'type':'string','x-mcp-header':'Q',**k}},'additionalProperties':False}
ADMITTED=[
 ('recommended no-parameter schema',tool(inputSchema=NONE),R26),
 ('no-parameter schema, older revision',tool(inputSchema=NONE),R06),
 ('schema dialect is declared',tool(inputSchema={**CLOSED,'$schema':'https://json-schema.org/draft/2020-12/schema'}),R26),
 ('name without a description',tool(),R26),
 ('camelCase name',tool(name='getUser'),R26),
 ('mixed name',tool(name='DATA_EXPORT_v2'),R26),
 ('dotted name',tool(name='admin.tools.list'),R26),
 ('one-character name',tool(name='x'),R26),
 ('128-character name',tool(name='a'*128),R26),
 ('title on the oldest revision',tool(title='Search'),R06),
 ('icons from 2025-11-25',tool(icons=[{'src':'https://mcp.example.test/i.png'}]),R25),
 ('Base64 icon',tool(icons=[{'src':'data:image/png;base64,iVBORw0KGgo=','sizes':['any']}]),R26),
 ('execution forbids tasks',tool(execution={'taskSupport':'forbidden'}),R25),
 ('$ref under a property',tool(inputSchema={**CLOSED,'properties':{'q':{'$ref':'#/$defs/q'}},'$defs':{'q':{'type':'string'}}}),R26),
 ('closed oneOf branches',tool(inputSchema={'type':'object','oneOf':[{'properties':{'a':{'type':'string'}},'required':['a'],'additionalProperties':False},{'properties':{'b':{'type':'string'}},'required':['b'],'additionalProperties':False}]}),R26),
 ('branches closed through $ref',tool(inputSchema={'type':'object','anyOf':[{'$ref':'#/$defs/a'}],'$defs':{'a':{'type':'object','additionalProperties':False}}}),R26),
 ('allOf closed by unevaluatedProperties',tool(inputSchema={'type':'object','allOf':[{'properties':{'a':{'type':'string'}}}],'unevaluatedProperties':False}),R26),
 ('required property defined in a branch',tool(inputSchema={'type':'object','required':['a'],'oneOf':[{'properties':{'a':{'type':'string'}},'additionalProperties':False}]}),R26),
 ('array output',tool(outputSchema={'type':'array','items':CLOSED}),R26),
 ('nullable object output',tool(outputSchema={**CLOSED,'type':['object','null']}),R26),
 ('scalar output',tool(outputSchema={'type':'string'}),R26),
 ('union output',tool(outputSchema={'oneOf':[{'type':'string'},CLOSED]}),R26),
 ('header on a nested property',tool(inputSchema={'type':'object','properties':{'a':{'type':'object','properties':{'b':{'type':'integer','x-mcp-header':'B'}}}},'additionalProperties':False}),R26),
 ('header token characters',tool(inputSchema=prop(**{'x-mcp-header':"A-b_c.d!#$%&'*+^`|~1"})),R26),
]
REFUSED=[
 ('unknown key',tool(hidden=True),R26,'unreviewed keys'),
 ('icons before 2025-11-25',tool(icons=[{'src':'https://mcp.example.test/i.png'}]),R06,'unreviewed keys'),
 ('execution before 2025-11-25',tool(execution={}),R06,'unreviewed keys'),
 ('execution after Tasks left the core',tool(execution={}),R26,'unreviewed keys'),
 ('optional task support',tool(execution={'taskSupport':'optional'}),R25,'task-augmented'),
 ('required task support',tool(execution={'taskSupport':'required'}),R25,'task-augmented'),
 ('name with a space',tool(name='search notes'),R26,'tool-name'),
 ('129-character name',tool(name='a'*129),R26,'tool-name'),
 ('empty name',tool(name=''),R26,'tool-name'),
 ('non-string name',tool(name=7),R26,'tool-name'),
 ('non-string title',tool(title=1),R26,'title and description'),
 ('non-string description',tool(description=None),R26,'title and description'),
 ('missing inputSchema',{'name':'a'},R26,'inputSchema'),
 ('null inputSchema',tool(inputSchema=None),R26,'inputSchema'),
 ('non-object input root',tool(inputSchema={'type':'array','items':NONE}),R26,'inputSchema'),
 ('open input',tool(inputSchema=OPEN),R26,'inputSchema'),
 ('open map input',tool(inputSchema={**OPEN,'additionalProperties':{'type':'string'}}),R26,'inputSchema'),
 ('required not declared',tool(inputSchema={**NONE,'required':['q']}),R26,'inputSchema'),
 ('unhashable required entry',tool(inputSchema={**NONE,'required':[{}]}),R26,'inputSchema'),
 ('properties not an object',tool(inputSchema={**NONE,'properties':[]}),R26,'inputSchema'),
 ('open oneOf branch',tool(inputSchema={'type':'object','oneOf':[{'properties':{}},{'additionalProperties':False}]}),R26,'inputSchema'),
 ('empty oneOf',tool(inputSchema={'type':'object','oneOf':[]}),R26,'inputSchema'),
 ('dangling $ref',tool(inputSchema={'type':'object','$ref':'#/$defs/a'}),R26,'inputSchema'),
 ('cyclic $ref',tool(inputSchema={'type':'object','$ref':'#/$defs/a','$defs':{'a':{'$ref':'#/$defs/a'}}}),R26,'inputSchema'),
 ('network $ref',tool(inputSchema={**CLOSED,'properties':{'q':{'$ref':'https://evil.example.test/s.json'}}}),R26,'inputSchema'),
 ('network $dynamicRef',tool(inputSchema={**CLOSED,'$dynamicRef':'https://evil.example.test/s.json'}),R26,'inputSchema'),
 ('non-string dialect',tool(inputSchema={**CLOSED,'$schema':1}),R26,'inputSchema'),
 ('empty output schema',tool(outputSchema={}),R26,'outputSchema'),
 ('open output',tool(outputSchema=OPEN),R26,'outputSchema'),
 ('array of open objects',tool(outputSchema={'type':'array','items':OPEN}),R26,'outputSchema'),
 ('array without items',tool(outputSchema={'type':'array'}),R26,'outputSchema'),
 ('unknown type name',tool(outputSchema={'type':'text'}),R26,'outputSchema'),
 ('array output before 2026-07-28',tool(outputSchema={'type':'array','items':CLOSED}),R25,'object root'),
 ('scalar output before 2026-07-28',tool(outputSchema={'type':'string'}),R06,'object root'),
 ('annotations not an object',tool(annotations=[]),R26,'annotations'),
 ('hint not boolean',tool(annotations={'readOnlyHint':'yes'}),R26,'annotations'),
 ('annotation title not a string',tool(annotations={'title':1}),R26,'annotations'),
 ('unknown hint',tool(annotations={'trustedHint':True}),R26,'annotations'),
 ('icons not a list',tool(icons={}),R26,'icons'),
 ('icon without src',tool(icons=[{}]),R26,'icons'),
 ('icon unknown key',tool(icons=[{'src':'https://mcp.example.test/i.png','onload':'x'}]),R26,'icons'),
 ('javascript icon',tool(icons=[{'src':'javascript:alert(1)'}]),R26,'icons'),
 ('file icon',tool(icons=[{'src':'file:///etc/passwd'}]),R26,'icons'),
 ('cleartext icon',tool(icons=[{'src':'http://mcp.example.test/i.png'}]),R26,'icons'),
 ('data icon that is not an image',tool(icons=[{'src':'data:text/html;base64,PHNjcmlwdD4='}]),R26,'icons'),
 ('unknown icon theme',tool(icons=[{'src':'https://mcp.example.test/i.png','theme':'neon'}]),R26,'icons'),
 ('icon sizes not strings',tool(icons=[{'src':'https://mcp.example.test/i.png','sizes':[48]}]),R26,'icons'),
 ('_meta not an object',tool(_meta=[]),R26,'_meta'),
 ('empty header',tool(inputSchema=prop(**{'x-mcp-header':''})),R26,'x-mcp-header'),
 ('header with a space',tool(inputSchema=prop(**{'x-mcp-header':'A B'})),R26,'x-mcp-header'),
 ('header injection',tool(inputSchema=prop(**{'x-mcp-header':'A\r\nX: y'})),R26,'x-mcp-header'),
 ('header not a string',tool(inputSchema=prop(**{'x-mcp-header':1})),R26,'x-mcp-header'),
 ('header on number',tool(inputSchema=prop(type='number')),R26,'x-mcp-header'),
 ('header on object',tool(inputSchema=prop(type='object')),R26,'x-mcp-header'),
 ('header on a type union',tool(inputSchema=prop(type=['string','null'])),R26,'x-mcp-header'),
 ('headers differ only by case',tool(inputSchema={'type':'object','properties':{'a':{'type':'string','x-mcp-header':'Region'},'b':{'type':'string','x-mcp-header':'REGION'}},'additionalProperties':False}),R26,'x-mcp-header'),
 ('header under items',tool(inputSchema={'type':'object','properties':{'a':{'type':'array','items':{'type':'object','properties':{'b':{'type':'string','x-mcp-header':'B'}}}}},'additionalProperties':False}),R26,'x-mcp-header'),
 ('header under oneOf',tool(inputSchema={'type':'object','oneOf':[{'properties':{'b':{'type':'string','x-mcp-header':'B'}},'additionalProperties':False}]}),R26,'x-mcp-header'),
 ('header behind $ref',tool(inputSchema={'type':'object','properties':{'a':{'$ref':'#/$defs/a'}},'$defs':{'a':{'type':'string','x-mcp-header':'A'}},'additionalProperties':False}),R26,'x-mcp-header'),
 ('header on the root',tool(inputSchema={**NONE,'x-mcp-header':'A'}),R26,'x-mcp-header'),
]
for label,item,version in ADMITTED:
    got=m.tool_problem(item,version,True);assert got is None,(label,got)
for label,item,version,reason in REFUSED:
    got=m.tool_problem(item,version,True);assert got and reason in got,(label,got)
bad=prop(type='number')
assert m.tool_problem(tool(inputSchema=bad),R26,False) is None,'stdio may ignore x-mcp-header'
assert m.tool_problem(tool(inputSchema=bad),R25,True) is None,'x-mcp-header is defined from 2026-07-28'
PY
echo "MCP session fixtures passed"
