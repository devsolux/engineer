#!/usr/bin/env python3
'''Validate MCP server authorization, capabilities, tools, and captured calls.'''
from __future__ import annotations
import argparse,hashlib,json,re,subprocess,sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file
HEX=re.compile(r'^[0-9a-f]{64}$');NAME=re.compile(r'^[a-z][a-z0-9_.-]{1,63}$')
MUTATING={'write','money','auth','admin','external_message','production','network'}
SUPPORTED_PROTOCOL_VERSIONS={'2025-06-18','2025-11-25'}
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else None
    except ValueError:return None
def https(v:Any)->bool:
    try:return text(v) and urlparse(v).scheme=='https' and bool(urlparse(v).netloc) and not urlparse(v).fragment
    except ValueError:return False
def sha_bytes(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def canonical_sha(v:Any)->str:return sha_bytes(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def safe_schema(v:Any)->bool:
    return isinstance(v,dict) and v.get('type')=='object' and isinstance(v.get('properties'),dict) and isinstance(v.get('required'),list) and set(v['required']).issubset(v['properties']) and v.get('additionalProperties') is False
def validate(d:Any,evidence_root:Path)->tuple[list[str],list[str]]:
    e=[];g=[];root={'schema_version','receipt_kind','server','authorization','capabilities','tools','calls','tests','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=root:e.append(f'root keys must be exactly {sorted(root)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_session'}:e.append('invalid receipt_kind')
    s=d.get('server',{});skeys={'name','version','revision_sha256','owner','purpose','environment','transport','endpoint','tls','sandboxed','egress','secret_classes','protocol_version','tools_snapshot_path','tools_snapshot_sha256','capture_manifest_path','capture_manifest_sha256'}
    if set(s)!=skeys or not NAME.fullmatch(str(s.get('name',''))) or not all(text(s.get(k)) for k in ('version','owner','purpose','environment','protocol_version','tools_snapshot_path','capture_manifest_path')) or s.get('protocol_version') not in SUPPORTED_PROTOCOL_VERSIONS or any(not HEX.fullmatch(str(s.get(k,''))) for k in ('revision_sha256','tools_snapshot_sha256','capture_manifest_sha256')) or s.get('transport') not in {'streamable_http','stdio'} or not isinstance(s.get('egress'),list) or any(not https(x) for x in s.get('egress',[])) or not isinstance(s.get('secret_classes'),list) or any(not text(x) for x in s.get('secret_classes',[])) or s.get('sandboxed') is not True:g.append('server identity, supported protocol, provenance, sandbox, or egress invalid')
    manifest=None;manifest_path=None;mrel=PurePosixPath(str(s.get('capture_manifest_path','')))
    if mrel.is_absolute() or '..' in mrel.parts:g.append('capture manifest path escapes evidence root')
    else:
        manifest_path=(evidence_root/Path(*mrel.parts)).resolve()
        try:manifest_path.relative_to(evidence_root.resolve());mraw=manifest_path.read_bytes();manifest=json.loads(mraw)
        except (ValueError,OSError,json.JSONDecodeError) as ex:g.append(f'capture manifest unreadable: {ex}');manifest_path=None
        if manifest_path:
            if sha_bytes(mraw)!=s.get('capture_manifest_sha256'):g.append('capture manifest digest mismatch')
            try:run=subprocess.run([sys.executable,str(Path(__file__).with_name('compile-mcp-transcript.py')),'--check-manifest',s['capture_manifest_path'],'--evidence-root',str(evidence_root)],capture_output=True,text=True,timeout=15);compiled=run.returncode==0
            except subprocess.TimeoutExpired:compiled=False
            if not compiled:g.append('capture manifest fails deterministic transcript compilation')
            protocol=manifest.get('protocol',{}) if isinstance(manifest,dict) else {}
            if protocol.get('protocol_version')!=s.get('protocol_version') or protocol.get('transport')!=s.get('transport') or protocol.get('server_info',{}).get('name')!=s.get('name') or protocol.get('server_info',{}).get('version')!=s.get('version'):g.append('capture manifest server identity differs from receipt')
    remote=s.get('transport')=='streamable_http'
    if remote and (not https(s.get('endpoint')) or s.get('tls') is not True):g.append('remote MCP endpoint requires HTTPS')
    a=d.get('authorization',{});akeys={'mode','protected_resource_metadata','authorization_server_metadata','protected_resource_401_discovery','protected_resource_path_discovery','protected_resource_root_fallback','oauth_metadata_discovery','oidc_metadata_discovery','selected_issuer_allowed','client_registration_mode','client_id','client_metadata_ssrf_mitigated','localhost_redirect_impersonation_mitigated','resource_indicator','authorization_resource_match','pkce_s256','state_validated','exact_redirect','scope_challenge_parsed','step_up_supported','token_in_query','audience_validated','token_passthrough','upstream_separate_token','token_storage','requested_scopes','granted_scopes','incremental_elevation'}
    registration=a.get('client_registration_mode')
    if set(a)!=akeys or a.get('mode') not in {'oauth2_1','stdio_env'} or registration not in {'pre_registered','client_id_metadata','dynamic'} or not text(a.get('client_id')) or not text(a.get('token_storage')) or not isinstance(a.get('requested_scopes'),list) or not isinstance(a.get('granted_scopes'),list) or any(not text(x) for x in a.get('requested_scopes',[])+a.get('granted_scopes',[])):e.append('authorization shape invalid')
    if registration=='client_id_metadata' and (not https(a.get('client_id')) or a.get('client_metadata_ssrf_mitigated') is not True or a.get('localhost_redirect_impersonation_mitigated') is not True):g.append('client ID metadata registration lacks SSRF or localhost impersonation controls')
    if remote and (a.get('mode')!='oauth2_1' or not https(a.get('protected_resource_metadata')) or not https(a.get('authorization_server_metadata')) or a.get('resource_indicator')!=s.get('endpoint') or any(a.get(k) is not True for k in ('protected_resource_401_discovery','protected_resource_path_discovery','protected_resource_root_fallback','oauth_metadata_discovery','oidc_metadata_discovery','selected_issuer_allowed','authorization_resource_match','pkce_s256','state_validated','exact_redirect','scope_challenge_parsed','step_up_supported','audience_validated','upstream_separate_token','incremental_elevation')) or a.get('token_in_query') is not False or a.get('token_passthrough') is not False):g.append('remote OAuth discovery, registration, PKCE, scope, audience, redirect, or token policy invalid')
    if not set(a.get('granted_scopes',[])).issubset(set(a.get('requested_scopes',[]))) or any(x in {'*','all','full-access'} for x in a.get('requested_scopes',[])):g.append('scope request or grant is overbroad')
    cap=d.get('capabilities',{});ckeys={'negotiated','roots','sampling','elicitation'}
    if set(cap)!=ckeys or not isinstance(cap.get('negotiated'),list) or any(x not in {'tools','resources','prompts','completions','logging','sampling','roots','elicitation'} for x in cap.get('negotiated',[])):e.append('capability negotiation invalid')
    if manifest:
        observed=set(manifest.get('protocol',{}).get('capabilities',{}));declared=set(cap.get('negotiated',[]))&{'tools','resources','prompts','completions','logging'}
        if observed!=declared:g.append('server capabilities differ from transcript compilation')
    roots=cap.get('roots',{});rkeys={'enabled','uris','consented','path_validation','list_changes'}
    if set(roots)!=rkeys or not isinstance(roots.get('enabled'),bool) or not isinstance(roots.get('uris'),list) or any(not text(x) or not x.startswith('file://') or '..' in x for x in roots.get('uris',[])) or (roots.get('enabled') and (roots.get('consented') is not True or roots.get('path_validation') is not True)):g.append('root capability unsafe')
    sampling=cap.get('sampling',{});spkeys={'enabled','human_review_request','human_review_response','model_hints_advisory','rate_limited'}
    if set(sampling)!=spkeys or not isinstance(sampling.get('enabled'),bool) or (sampling.get('enabled') and any(sampling.get(k) is not True for k in spkeys-{'enabled'})):g.append('sampling lacks human or budget control')
    elic=cap.get('elicitation',{});ekeys={'enabled','modes','server_identity_shown','decline_supported','rate_limited','form','url'}
    form=elic.get('form',{});fkeys={'enabled','sensitive_requested','schema_validated','clickable_urls'}
    url=elic.get('url',{});ukeys={'enabled','explicit_consent','auto_fetch','auto_open','full_url_shown','domain_highlighted','client_content_access','sensitive_url_data','preauthenticated_url','https_only','user_binding_verified','completion_ids_validated','manual_resume_supported'}
    modes=elic.get('modes',[])
    if set(elic)!=ekeys or not isinstance(elic.get('enabled'),bool) or not isinstance(modes,list) or len(modes)!=len(set(modes)) or any(x not in {'form','url'} for x in modes) or elic.get('enabled')!=bool(modes) or (elic.get('enabled') and any(elic.get(k) is not True for k in ('server_identity_shown','decline_supported','rate_limited'))):g.append('elicitation identity, modes, consent, or rate control invalid')
    if set(form)!=fkeys or form.get('enabled')!=('form' in modes) or (form.get('enabled') and (form.get('sensitive_requested') is not False or form.get('schema_validated') is not True or form.get('clickable_urls') is not False)):g.append('form elicitation may not collect secrets or carry clickable URLs')
    if set(url)!=ukeys or url.get('enabled')!=('url' in modes) or (url.get('enabled') and (any(url.get(k) is not True for k in ukeys-{'enabled','auto_fetch','auto_open','client_content_access','sensitive_url_data','preauthenticated_url'}) or any(url.get(k) is not False for k in ('auto_fetch','auto_open','client_content_access','sensitive_url_data','preauthenticated_url')))):g.append('URL elicitation isolation, consent, URL, identity, or completion control invalid')
    for name,obj in [('roots',roots),('sampling',sampling),('elicitation',elic)]:
        if obj.get('enabled')!=(name in cap.get('negotiated',[])):g.append(f'{name} capability declaration mismatch')
    snapshot={}; rel=PurePosixPath(str(s.get('tools_snapshot_path','')))
    if rel.is_absolute() or '..' in rel.parts:g.append('tools snapshot path escapes evidence root')
    else:
        path=(evidence_root/Path(*rel.parts)).resolve(); root=evidence_root.resolve()
        try:path.relative_to(root)
        except ValueError:g.append('tools snapshot path escapes evidence root');path=None
        if path:
            try:
                raw=path.read_bytes()
                if sha_bytes(raw)!=s.get('tools_snapshot_sha256'):g.append('tools snapshot digest mismatch')
                snap=json.loads(raw); listed=snap.get('tools',[]) if isinstance(snap,dict) and set(snap)=={'tools'} else []
                if not listed:g.append('tools snapshot shape invalid')
                for i,item in enumerate(listed):
                    if not isinstance(item,dict) or set(item)!={'name','description','inputSchema','outputSchema'} or not NAME.fullmatch(str(item.get('name',''))) or not text(item.get('description')) or not safe_schema(item.get('inputSchema')) or not safe_schema(item.get('outputSchema')) or item.get('name') in snapshot:g.append(f'tools snapshot item {i} invalid')
                    else:snapshot[item['name']]=item
            except (OSError,json.JSONDecodeError) as ex:g.append(f'tools snapshot unreadable: {ex}')
    if manifest and snapshot:
        out=manifest.get('outputs',{}).get('tools_list',{})
        if out.get('canonical_sha256')!=canonical_sha({'tools':list(snapshot.values())}):g.append('tools snapshot differs from transcript-compiled output')
    tools=d.get('tools',[]);tmap={};tkeys={'name','description_sha256','input_schema_sha256','output_schema_sha256','risk','scopes','destinations','timeout_ms','rate_limit','idempotency_required','confirmation_required','input_validated','output_validated','output_sanitized'}
    if not isinstance(tools,list) or not tools:e.append('tools required');tools=[]
    for i,t in enumerate(tools):
        if not isinstance(t,dict) or set(t)!=tkeys:e.append(f'tool {i} keys invalid');continue
        name=t.get('name')
        if not NAME.fullmatch(str(name or '')) or name in tmap or any(not HEX.fullmatch(str(t.get(k,''))) for k in ('description_sha256','input_schema_sha256','output_schema_sha256')) or t.get('risk') not in {'read'}|MUTATING or not isinstance(t.get('scopes'),list) or not t.get('scopes') or not isinstance(t.get('destinations'),list) or not t.get('destinations') or any(not https(x) for x in t.get('destinations',[])) or not isinstance(t.get('timeout_ms'),int) or not 1<=t.get('timeout_ms',0)<=120000 or not text(t.get('rate_limit')):e.append(f'tool {i} identity or bounds invalid');continue
        tmap[name]=t
        captured=snapshot.get(name)
        if not captured:g.append(f'tool {name} missing from captured snapshot')
        elif t.get('description_sha256')!=sha_bytes(captured['description'].encode()) or t.get('input_schema_sha256')!=canonical_sha(captured['inputSchema']) or t.get('output_schema_sha256')!=canonical_sha(captured['outputSchema']):g.append(f'tool {name} metadata differs from captured snapshot')
        if not set(t.get('scopes',[])).issubset(set(a.get('granted_scopes',[]))):g.append(f'tool {name} scopes exceed grant')
        if any(x not in s.get('egress',[]) and not any(x.startswith(base.rstrip('/')+'/') for base in s.get('egress',[])) for x in t.get('destinations',[])):g.append(f'tool {name} destination outside server egress')
        if any(t.get(k) is not True for k in ('input_validated','output_validated','output_sanitized')):g.append(f'tool {name} validation incomplete')
        if t.get('risk') in MUTATING and (t.get('confirmation_required') is not True or t.get('idempotency_required') is not True):g.append(f'tool {name} mutation lacks confirmation or idempotency')
    if set(tmap)!=set(snapshot):g.append('receipt tool set differs from captured snapshot')
    calls=d.get('calls',[]);ids=set();callkeys={'id','tool','user_id','tenant_id','scopes','args_sha256','result_sha256','destination','root_uri','started_at','completed_at','authorized','schema_matched','confirmed','confirmation_id','idempotency_key','timed_out','rate_limited','sensitive_input','sensitive_output','source_trust','is_error','audit_event'}
    if not isinstance(calls,list) or not calls:e.append('captured calls required');calls=[]
    for i,c in enumerate(calls):
        if not isinstance(c,dict) or set(c)!=callkeys:e.append(f'call {i} keys invalid');continue
        cid=c.get('id');tool=tmap.get(c.get('tool'));start,end=ts(c.get('started_at')),ts(c.get('completed_at'))
        if not text(cid) or cid in ids or not tool or not all(text(c.get(k)) for k in ('user_id','tenant_id','audit_event')) or not HEX.fullmatch(str(c.get('args_sha256',''))) or not HEX.fullmatch(str(c.get('result_sha256',''))) or not start or not end or end<start or c.get('source_trust') not in {'untrusted','verified'} or not all(isinstance(c.get(k),bool) for k in ('authorized','schema_matched','confirmed','timed_out','rate_limited','sensitive_input','sensitive_output','is_error')):e.append(f'call {i} identity or evidence invalid');continue
        ids.add(cid)
        if c.get('destination') not in tool.get('destinations',[]) or c.get('root_uri') not in roots.get('uris',[]):g.append(f'call {cid} destination or root outside policy')
        if not set(tool.get('scopes',[])).issubset(set(c.get('scopes',[]))) or not set(c.get('scopes',[])).issubset(set(a.get('granted_scopes',[]))):g.append(f'call {cid} scope invalid')
        if c.get('authorized') is not True or c.get('schema_matched') is not True or c.get('timed_out') or c.get('sensitive_input') or c.get('sensitive_output'):g.append(f'call {cid} authorization, schema, timeout, or sensitivity invalid')
        if (end-start).total_seconds()*1000>tool.get('timeout_ms',0):g.append(f'call {cid} exceeded timeout budget')
        if tool.get('risk') in MUTATING and (c.get('confirmed') is not True or not text(c.get('confirmation_id')) or not text(c.get('idempotency_key'))):g.append(f'call {cid} mutation evidence incomplete')
        if tool.get('risk')=='read' and (c.get('confirmed') or c.get('confirmation_id') is not None or c.get('idempotency_key') is not None):g.append(f'call {cid} unexpected authority artifact')
    tests=d.get('tests',{});required={'wrong_audience','token_passthrough','scope_escalation','schema_drift','prompt_injection','cross_tenant','root_traversal','elicitation_form_secret','elicitation_url_auto_open','elicitation_url_prefetch','elicitation_url_sensitive_data','elicitation_url_user_binding','elicitation_url_client_observation','sampling_without_approval','timeout','passed'}
    if set(tests)!=required or any(tests.get(k) is not True for k in required):g.append('MCP security regression coverage incomplete')
    review=d.get('review',{});ra,rb=ts(review.get('reviewed_at')),ts(review.get('review_after'))
    if set(review)!={'owner','independent_reviewer','reviewed_at','review_after','approved','rollback'} or not all(text(review.get(k)) for k in ('owner','independent_reviewer','rollback')) or review.get('owner')==review.get('independent_reviewer') or not ra or not rb or rb<=ra or not isinstance(review.get('approved'),bool):g.append('independent review invalid')
    dec=d.get('decision',{})
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'trust','quarantine','reject'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or any(not text(x) for x in dec.get('reasons',[])) or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    if dec.get('outcome')=='trust' and (kind!='captured_session' or review.get('approved') is not True or dec.get('unresolved_risks')):g.append('trust requires captured approved session with no unresolved risk')
    return e,g
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('--evidence-root',default='.');p.add_argument('--json',action='store_true');a=p.parse_args()
    path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d,Path(a.evidence_root));ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('MCP session valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
