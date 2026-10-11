#!/usr/bin/env python3
'''Validate an agent-controlled browser session policy and observed receipt.'''

from __future__ import annotations
import argparse, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, urlparse

sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX=re.compile(r'^[0-9a-f]{64}$')
PERMS={'clipboard','geolocation','notifications','camera','microphone','downloads','uploads','extensions','filesystem'}
SAFE_ACTIONS={'navigate','read','screenshot','assert'}
MUTATIONS={'click_submit','fill_sensitive','login','message','post','invite','payment','account_change','permission_change','delete','upload','download','clipboard_write'}
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def rel(v:Any):
    if not text(v):return None
    p=PurePosixPath(v);return None if p.is_absolute() or '..' in p.parts or '.' in p.parts else p
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else None
    except ValueError:return None
def origin(v:Any):
    if not text(v):return None
    u=urlparse(v)
    if u.scheme not in {'http','https'} or not u.hostname or u.username or u.password:return None
    return f'{u.scheme}://{u.netloc}'

def validate(d:Any,path:Path)->tuple[list[str],list[str]]:
    e=[];g=[]
    keys={'schema_version','receipt_kind','session','policy','artifacts','observations','cleanup','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=keys:e.append(f'root keys must be exactly {sorted(keys)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_session'}:e.append('invalid receipt_kind')
    s=d.get('session',{});skeys={'id','environment','risk_class','role','auth_mode','lane','worker_id','namespace','account_id_sha256','tenant_id_sha256','context_id','profile','storage_state','started_at','ended_at'}
    if set(s)!=skeys:e.append('session keys invalid')
    if not all(text(s.get(k)) for k in ('id','environment','role','lane','worker_id','namespace','context_id')) or s.get('environment') not in {'local','preview','staging','production','external'} or s.get('risk_class') not in {'public_read','auth_read','fixture_write','external_mutation'} or s.get('auth_mode') not in {'logged_out','synthetic','dedicated_low_privilege'} or s.get('profile')!='ephemeral_nonpersistent':g.append('session identity or isolation invalid')
    if s.get('risk_class')=='public_read' and (s.get('account_id_sha256') is not None or s.get('tenant_id_sha256') is not None):g.append('public session cannot declare account or tenant identity')
    if s.get('risk_class')!='public_read' and not HEX.fullmatch(str(s.get('account_id_sha256',''))):g.append('authenticated session requires a hashed account identity')
    if s.get('risk_class')=='fixture_write' and not HEX.fullmatch(str(s.get('tenant_id_sha256',''))):g.append('fixture write requires a hashed tenant identity')
    if s.get('tenant_id_sha256') is not None and not HEX.fullmatch(str(s.get('tenant_id_sha256',''))):g.append('tenant identity must be null or a SHA-256 value')
    started,ended=ts(s.get('started_at')),ts(s.get('ended_at'))
    if not started or not ended or started>=ended:e.append('session timestamps invalid')
    storage=s.get('storage_state')
    if not isinstance(storage,dict) or set(storage)!={'used','source','retained','committed','shared_between_workers'}:e.append('storage_state invalid')
    elif storage.get('retained') is not False or storage.get('committed') is not False or storage.get('shared_between_workers') is not False:g.append('auth storage must not be retained, committed, or shared')
    elif s.get('auth_mode')=='logged_out' and (storage.get('used') is not False or storage.get('source') is not None):g.append('logged-out session cannot use storage state')
    elif s.get('auth_mode')!='logged_out' and (storage.get('used') is not True or not text(storage.get('source'))):g.append('authenticated session requires a declared storage source')

    p=d.get('policy',{});pkeys={'allowed_origins','initial_urls','network','permissions','actions','data','artifacts','stop_conditions'}
    if set(p)!=pkeys:e.append('policy keys invalid')
    allowed=p.get('allowed_origins',[])
    if not isinstance(allowed,list) or not allowed or any(origin(x)!=x for x in allowed):e.append('allowed_origins must contain canonical HTTP(S) origins')
    initial=p.get('initial_urls',[])
    if not isinstance(initial,list) or not initial or any(origin(x) not in allowed for x in initial):e.append('initial_urls must use allowed origins')
    net=p.get('network',{})
    if set(net)!={'subresources','redirects','page_derived_urls','exact_url_allowlist','forbidden_query_keys'} or net.get('subresources') not in {'allowed_origins_only','first_party_only'} or net.get('redirects')!='allowed_origins_only' or net.get('page_derived_urls')!='exact_allowlist_or_user_approval' or not isinstance(net.get('exact_url_allowlist'),list) or any(origin(x) not in allowed for x in net.get('exact_url_allowlist',[])) or not isinstance(net.get('forbidden_query_keys'),list) or not net.get('forbidden_query_keys'):g.append('network source-to-sink policy incomplete')
    perms=p.get('permissions',{})
    if set(perms)!=PERMS or any(v not in {'deny','fixture_only'} for v in perms.values()):e.append('permission policy invalid')
    acts=p.get('actions',{})
    if set(acts)!={'allowed','mutations','always_ask'} or not isinstance(acts.get('allowed'),list) or any(x not in SAFE_ACTIONS|MUTATIONS for x in acts.get('allowed',[])) or not isinstance(acts.get('mutations'),list) or any(not text(x.get('id')) or x.get('kind') not in MUTATIONS or not text(x.get('target')) or x.get('approved') is not True for x in acts.get('mutations',[]) if isinstance(x,dict)) or any(not isinstance(x,dict) for x in acts.get('mutations',[])) or not isinstance(acts.get('always_ask'),list) or not {'login','payment','message','post','invite','account_change','permission_change','delete','upload','download'}.issubset(set(acts.get('always_ask',[]))):g.append('action or always-ask policy incomplete')
    if s.get('risk_class') in {'public_read','auth_read'} and acts.get('mutations'):g.append('read-only session cannot declare mutations')
    data=p.get('data',{})
    if set(data)!={'allowed_classes','prohibited_classes','url_values_must_be_public','page_content_untrusted'} or not isinstance(data.get('allowed_classes'),list) or not isinstance(data.get('prohibited_classes'),list) or not {'credentials','cookies','tokens','customer_data','private_files','clipboard'}.issubset(set(data.get('prohibited_classes',[]))) or data.get('url_values_must_be_public') is not True or data.get('page_content_untrusted') is not True:g.append('browser data policy incomplete')
    ap=p.get('artifacts',{})
    if set(ap)!={'redact','auth_state_forbidden','failure_only','retention'} or ap.get('redact') is not True or ap.get('auth_state_forbidden') is not True or ap.get('failure_only') is not True or not text(ap.get('retention')):g.append('artifact policy incomplete')
    if not isinstance(p.get('stop_conditions'),list) or not {'prompt_injection','unexpected_origin','auth_boundary_change','permission_prompt','captcha','ambiguous_mutation'}.issubset(set(p.get('stop_conditions',[]))):g.append('browser stop conditions incomplete')

    arts=d.get('artifacts',[]);amap={}
    if not isinstance(arts,list) or not arts:e.append('artifacts required');arts=[]
    for i,a in enumerate(arts):
        if not isinstance(a,dict) or set(a)!={'id','kind','path','sha256','redacted','contains_auth_state'}:e.append(f'artifact {i} keys invalid');continue
        aid=a.get('id');rp=rel(a.get('path'))
        if not text(aid) or aid in amap or a.get('kind') not in {'summary','screenshot','trace','har'} or not rp or not HEX.fullmatch(str(a.get('sha256',''))) or a.get('redacted') is not True or a.get('contains_auth_state') is not False:e.append(f'artifact {i} invalid');continue
        fp=path.parent/rp
        if not fp.is_file() or sha(fp)!=a['sha256']:e.append(f'artifact {aid} missing or hash mismatch')
        amap[aid]=a
    o=d.get('observations',{});okeys={'navigations','requests','actions','popups','transfers','permission_prompts','injection','console_errors','page_errors','final_url','artifact_ids'}
    if set(o)!=okeys:e.append('observation keys invalid')
    forbidden={x.lower() for x in net.get('forbidden_query_keys',[])}
    for i,n in enumerate(o.get('navigations',[]) if isinstance(o.get('navigations'),list) else []):
        if not isinstance(n,dict) or set(n)!={'url','source','user_approved','public_indexed','redirect'}:e.append(f'navigation {i} invalid');continue
        url=n.get('url');u=urlparse(url) if text(url) else None
        if not u or origin(url) not in allowed:g.append(f'navigation {i} used unexpected origin')
        if u and any(k.lower() in forbidden for k,_ in parse_qsl(u.query,keep_blank_values=True)):g.append(f'navigation {i} contains forbidden query key')
        if n.get('source') not in {'initial','user','page','redirect'} or not isinstance(n.get('user_approved'),bool) or not isinstance(n.get('public_indexed'),bool) or not isinstance(n.get('redirect'),bool):e.append(f'navigation {i} metadata invalid')
        if n.get('source') in {'page','redirect'} and url not in net.get('exact_url_allowlist',[]) and not n.get('public_indexed') and not n.get('user_approved'):g.append(f'navigation {i} page-derived URL lacks exact trust decision')
    requests=o.get('requests',[])
    if not isinstance(requests,list):e.append('requests must be an array');requests=[]
    for i,r in enumerate(requests):
        if not isinstance(r,dict) or set(r)!={'url','method','resource_type','initiator','blocked','sensitive_data'}:e.append(f'request {i} invalid');continue
        if origin(r.get('url')) not in allowed and r.get('blocked') is not True:g.append(f'request {i} escaped allowed origins')
        if r.get('sensitive_data') is not False:g.append(f'request {i} contains sensitive data')
    declared={x.get('id'):x for x in acts.get('mutations',[]) if isinstance(x,dict)}
    observed=o.get('actions',[])
    if not isinstance(observed,list):e.append('actions observations must be an array');observed=[]
    for i,a in enumerate(observed):
        if not isinstance(a,dict) or set(a)!={'id','kind','target','mutation','approval_id','source','artifact_ids'}:e.append(f'action {i} invalid');continue
        if a.get('kind') not in acts.get('allowed',[]):g.append(f'action {i} kind not allowed')
        if a.get('source') not in {'goal','test_spec','page_content'}:e.append(f'action {i} source invalid')
        approval=declared.get(a.get('approval_id'))
        if a.get('mutation') is True and (approval is None or approval.get('kind')!=a.get('kind') or approval.get('target')!=a.get('target')):g.append(f'action {i} mutation lacks exact kind-and-target approval')
        if a.get('source')=='page_content' and a.get('mutation') is True:g.append(f'action {i} lets page content authorize mutation')
        if not isinstance(a.get('artifact_ids'),list) or any(x not in amap for x in a.get('artifact_ids',[])):e.append(f'action {i} artifact refs invalid')
    pop=o.get('popups',[])
    if not isinstance(pop,list):e.append('popups must be an array')
    elif any(not isinstance(x,dict) or set(x)!={'url','expected','closed','origin_allowed'} or x.get('expected') is not True or x.get('closed') is not True or x.get('origin_allowed') is not True for x in pop):g.append('unexpected or uncontained popup observed')
    transfers=o.get('transfers',[])
    if not isinstance(transfers,list):e.append('transfers must be an array')
    else:
        for i,t in enumerate(transfers):
            if not isinstance(t,dict) or set(t)!={'kind','path','expected_sha256','quarantined','executed','approval_id'} or t.get('kind') not in {'download','upload','clipboard'}:e.append(f'transfer {i} invalid');continue
            rp=rel(t.get('path'))
            if not rp or not HEX.fullmatch(str(t.get('expected_sha256',''))) or perms.get({'download':'downloads','upload':'uploads','clipboard':'clipboard'}[t['kind']])!='fixture_only' or t.get('approval_id') not in declared or t.get('quarantined') is not True or t.get('executed') is not False:g.append(f'transfer {i} violates fixture quarantine policy')
    if o.get('permission_prompts')!=[]:g.append('unexpected browser permission prompt observed')
    inj=o.get('injection',{})
    if set(inj)!={'encountered','followed','source_to_sink_blocked','stopped','evidence'} or not isinstance(inj.get('encountered'),bool) or inj.get('followed') is not False or inj.get('source_to_sink_blocked') is not True or (inj.get('encountered') and inj.get('stopped') is not True) or not text(inj.get('evidence')):g.append('prompt-injection observation invalid')
    if not isinstance(o.get('console_errors'),list) or not isinstance(o.get('page_errors'),list) or origin(o.get('final_url')) not in allowed or not isinstance(o.get('artifact_ids'),list) or any(x not in amap for x in o.get('artifact_ids',[])):e.append('final observation evidence invalid')
    c=d.get('cleanup',{})
    if set(c)!={'context_closed','storage_deleted','downloads_deleted','fixture_data_deleted','namespace_verified','unexpected_pages_closed'} or any(c.get(k) is not True for k in c):g.append('browser cleanup incomplete')
    review=d.get('review',{})
    if set(review)!={'reviewer','policy_reviewed','evidence_reviewed','approved','notes'} or not text(review.get('reviewer')) or review.get('policy_reviewed') is not True or review.get('evidence_reviewed') is not True or not isinstance(review.get('approved'),bool) or not text(review.get('notes')):g.append('browser review invalid')
    dec=d.get('decision',{})
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'pass','fail','infrastructure_error'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    if dec.get('outcome')=='pass' and (kind!='captured_session' or review.get('approved') is not True or dec.get('unresolved_risks') or o.get('console_errors') or o.get('page_errors')):g.append('passing browser session requires captured clean evidence and approved review')
    return e,g

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('receipt',type=Path);p.add_argument('--json',action='store_true');a=p.parse_args();path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d,path);ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('browser session valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
