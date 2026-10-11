#!/usr/bin/env python3
'''Validate captured MCP resource and prompt catalogs/content against one admitted session.'''
from __future__ import annotations
import argparse,hashlib,json,re,subprocess,sys
from datetime import datetime
from pathlib import Path,PurePosixPath
from typing import Any
from urllib.parse import urlparse
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file
HEX=re.compile(r'^[0-9a-f]{64}$'); NAME=re.compile(r'^[a-z][a-z0-9_.-]{1,63}$')
INJECTION=re.compile(r'(?is)(ignore.{0,40}(instruction|policy|message)|(?:run|execute|invoke).{0,30}(?:shell|command|tool)|(?:reveal|print|send|exfiltrat).{0,30}(?:secret|token|key|credential|system prompt)|you are now|act as)')
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else None
    except ValueError:return None
def sha(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def csha(v:Any)->str:return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def suspicious(v:Any)->bool:return isinstance(v,str) and bool(INJECTION.search(v))
def confined(root:Path,value:Any)->tuple[Path|None,str|None]:
    if not text(value):return None,'path missing'
    rel=PurePosixPath(value)
    if rel.is_absolute() or '..' in rel.parts:return None,'path escapes evidence root'
    path=(root/Path(*rel.parts)).resolve()
    try:path.relative_to(root.resolve())
    except ValueError:return None,'path escapes evidence root'
    return path,None
def load_bound(root:Path,value:Any,digest:Any,label:str,e:list[str],g:list[str])->tuple[Any,Path|None]:
    path,why=confined(root,value)
    if why:g.append(f'{label} {why}');return None,None
    try:raw=path.read_bytes()
    except OSError as ex:g.append(f'{label} unreadable: {ex}');return None,path
    if not HEX.fullmatch(str(digest or '')) or sha(raw)!=digest:g.append(f'{label} digest mismatch')
    try:return json.loads(raw),path
    except json.JSONDecodeError as ex:e.append(f'{label} JSON invalid: {ex}');return None,path
def valid_uri(v:Any,schemes:set[str])->bool:
    try:u=urlparse(v);return text(v) and u.scheme in schemes and bool(u.netloc or u.path) and not u.fragment
    except ValueError:return False
def validate(d:Any,root:Path,validator:Path)->tuple[list[str],list[str]]:
    e=[];g=[];keys={'schema_version','receipt_kind','session','capture','capabilities','policy','resources','resource_templates','prompts','completions','tests','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=keys:e.append(f'root keys must be exactly {sorted(keys)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_content'}:e.append('receipt_kind invalid')
    binding=d.get('session',{}); bkeys={'path','sha256','server_name','server_revision_sha256','protocol_version'}
    if set(binding)!=bkeys or not all(text(binding.get(k)) for k in ('path','server_name','protocol_version')) or any(not HEX.fullmatch(str(binding.get(k,''))) for k in ('sha256','server_revision_sha256')):e.append('session binding invalid')
    session,session_path=load_bound(root,binding.get('path'),binding.get('sha256'),'session',e,g)
    session_valid=False
    if session_path and session is not None:
        try:run=subprocess.run([sys.executable,str(validator),str(session_path),'--evidence-root',str(root),'--json'],capture_output=True,text=True,timeout=15);session_valid=run.returncode==0
        except subprocess.TimeoutExpired:session_valid=False
        if not session_valid:g.append('bound MCP session fails canonical validation')
        server=session.get('server',{}) if isinstance(session,dict) else {}
        if binding.get('server_name')!=server.get('name') or binding.get('server_revision_sha256')!=server.get('revision_sha256') or binding.get('protocol_version')!=server.get('protocol_version'):g.append('session identity binding mismatch')
    capture=d.get('capture',{}); ckeys={'path','sha256','manifest_path','manifest_sha256','captured_at','pagination_complete','redacted'}
    if set(capture)!=ckeys or not ts(capture.get('captured_at')) or capture.get('pagination_complete') is not True or capture.get('redacted') is not True:e.append('capture metadata invalid')
    raw,_=load_bound(root,capture.get('path'),capture.get('sha256'),'content capture',e,g)
    manifest,manifest_path=load_bound(root,capture.get('manifest_path'),capture.get('manifest_sha256'),'capture manifest',e,g)
    if manifest_path and manifest is not None:
        try:run=subprocess.run([sys.executable,str(Path(__file__).with_name('compile-mcp-transcript.py')),'--check-manifest',capture['manifest_path'],'--evidence-root',str(root)],capture_output=True,text=True,timeout=15);compiled=run.returncode==0
        except subprocess.TimeoutExpired:compiled=False
        if not compiled:g.append('capture manifest fails deterministic transcript compilation')
        out=manifest.get('outputs',{}).get('server_content',{}) if isinstance(manifest,dict) else {}
        if raw is not None and out.get('canonical_sha256')!=csha(raw):g.append('content capture differs from transcript-compiled output')
    caps=d.get('capabilities',{}); capkeys={'resources','resources_subscribe','resources_list_changed','prompts','prompts_list_changed','completions'}
    if set(caps)!=capkeys or any(not isinstance(caps.get(k),bool) for k in capkeys):e.append('content capability shape invalid')
    if session_valid:
        negotiated=set(session.get('capabilities',{}).get('negotiated',[]))
        if caps.get('resources')!=('resources' in negotiated) or caps.get('prompts')!=('prompts' in negotiated):g.append('content capabilities differ from negotiated session')
    if manifest:
        mcaps=manifest.get('protocol',{}).get('capabilities',{});resources=mcaps.get('resources',{}) if isinstance(mcaps.get('resources'),dict) else {};prompts=mcaps.get('prompts',{}) if isinstance(mcaps.get('prompts'),dict) else {}
        expected={'resources':'resources' in mcaps,'resources_subscribe':resources.get('subscribe') is True,'resources_list_changed':resources.get('listChanged') is True,'prompts':'prompts' in mcaps,'prompts_list_changed':prompts.get('listChanged') is True,'completions':'completions' in mcaps}
        if any(caps.get(k)!=v for k,v in expected.items()):g.append('content capabilities differ from transcript compilation')
    policy=d.get('policy',{}); pkeys={'allowed_uri_schemes','max_item_bytes','resource_selection','prompt_selection','content_trust','annotations_advisory','argument_validation','embedded_resources_untrusted','completion_values_untrusted','list_change_revalidation','subscription_revalidation'}
    schemes=set(policy.get('allowed_uri_schemes',[])) if isinstance(policy.get('allowed_uri_schemes'),list) else set()
    if set(policy)!=pkeys or not schemes or any(not re.fullmatch(r'[a-z][a-z0-9+.-]*',str(x)) for x in schemes) or not isinstance(policy.get('max_item_bytes'),int) or not 1<=policy.get('max_item_bytes',0)<=10_000_000 or policy.get('resource_selection')!='application_or_user' or policy.get('prompt_selection')!='explicit_user' or policy.get('content_trust')!='untrusted_data' or any(policy.get(k) is not True for k in pkeys-{'allowed_uri_schemes','max_item_bytes','resource_selection','prompt_selection','content_trust'}):g.append('content trust policy invalid')
    catalog_resources={};catalog_templates={};catalog_prompts={};reads={};gets={};completions=[]
    rkeys={'resources','resourceTemplates','prompts','resourceReads','promptGets','completions'}
    if not isinstance(raw,dict) or set(raw)!=rkeys:e.append('content capture shape invalid');raw={k:[] for k in rkeys}
    for k in rkeys:
        if not isinstance(raw.get(k),list):e.append(f'capture {k} must be a list');raw[k]=[]
    for i,item in enumerate(raw['resources']):
        if not isinstance(item,dict) or set(item)!={'uri','name','mimeType'} or not valid_uri(item.get('uri'),schemes) or not all(text(item.get(k)) for k in ('name','mimeType')) or item.get('uri') in catalog_resources:e.append(f'resource catalog item {i} invalid')
        else:catalog_resources[item['uri']]=item
    for i,item in enumerate(raw['resourceTemplates']):
        if not isinstance(item,dict) or set(item)!={'uriTemplate','name','mimeType'} or not text(item.get('uriTemplate')) or '{' not in item.get('uriTemplate','') or not valid_uri(item.get('uriTemplate','').split('{',1)[0]+'x',schemes) or not all(text(item.get(k)) for k in ('name','mimeType')) or item.get('uriTemplate') in catalog_templates:e.append(f'resource template {i} invalid')
        else:catalog_templates[item['uriTemplate']]=item
    for i,item in enumerate(raw['prompts']):
        args=item.get('arguments',[]) if isinstance(item,dict) else []
        if not isinstance(item,dict) or set(item)!={'name','description','arguments'} or not NAME.fullmatch(str(item.get('name',''))) or not text(item.get('description')) or item.get('name') in catalog_prompts or not isinstance(args,list) or any(not isinstance(a,dict) or set(a)!={'name','description','required'} or not NAME.fullmatch(str(a.get('name',''))) or not text(a.get('description')) or not isinstance(a.get('required'),bool) for a in args) or len({a.get('name') for a in args})!=len(args):e.append(f'prompt catalog item {i} invalid')
        else:catalog_prompts[item['name']]=item
    for i,item in enumerate(raw['resourceReads']):
        contents=item.get('contents',[]) if isinstance(item,dict) else []
        if not isinstance(item,dict) or set(item)!={'uri','contents'} or item.get('uri') not in catalog_resources or item.get('uri') in reads or not isinstance(contents,list) or not contents:e.append(f'resource read {i} invalid');continue
        good=True
        for part in contents:
            if not isinstance(part,dict) or set(part)!={'uri','mimeType','text'} or part.get('uri')!=item.get('uri') or part.get('mimeType')!=catalog_resources[item['uri']]['mimeType'] or not isinstance(part.get('text'),str) or len(part['text'].encode())>policy.get('max_item_bytes',0) or suspicious(part.get('text')):good=False
        if not good:e.append(f'resource read {i} content invalid')
        else:reads[item['uri']]=item
    for i,item in enumerate(raw['promptGets']):
        messages=item.get('messages',[]) if isinstance(item,dict) else []; prompt=catalog_prompts.get(item.get('name')) if isinstance(item,dict) else None
        required={a['name'] for a in prompt.get('arguments',[]) if a['required']} if prompt else set();known={a['name'] for a in prompt.get('arguments',[])} if prompt else set();args=item.get('arguments',{}) if isinstance(item,dict) else {}
        good=prompt and isinstance(args,dict) and required.issubset(args) and set(args).issubset(known) and all(text(v) and not suspicious(v) for v in args.values()) and isinstance(messages,list) and bool(messages)
        if good:
            for m in messages:
                if not isinstance(m,dict) or set(m)!={'role','content'} or m.get('role') not in {'user','assistant'} or not isinstance(m.get('content'),dict) or set(m['content'])!={'type','text'} or m['content'].get('type')!='text' or not isinstance(m['content'].get('text'),str) or len(m['content']['text'].encode())>policy.get('max_item_bytes',0) or suspicious(m['content'].get('text')):good=False
        if not isinstance(item,dict) or set(item)!={'name','arguments','description','messages'} or not text(item.get('description')) or item.get('name') in gets or not good:e.append(f'prompt get {i} invalid')
        else:gets[item['name']]=item
    for i,item in enumerate(raw['completions']):
        ref=item.get('ref',{}) if isinstance(item,dict) else {};arg=item.get('argument',{}) if isinstance(item,dict) else {};values=item.get('values',[]) if isinstance(item,dict) else []
        prompt=catalog_prompts.get(ref.get('name')) if isinstance(ref,dict) and ref.get('type')=='ref/prompt' else None
        names={a['name'] for a in prompt.get('arguments',[])} if prompt else set()
        if not isinstance(item,dict) or set(item)!={'ref','argument','values','total','hasMore'} or set(ref)!={'type','name'} or set(arg)!={'name','value'} or not prompt or arg.get('name') not in names or not text(arg.get('value')) or suspicious(arg.get('value')) or not isinstance(values,list) or not values or any(not text(v) or suspicious(v) for v in values) or not isinstance(item.get('total'),int) or item.get('total')<len(values) or not isinstance(item.get('hasMore'),bool):e.append(f'completion {i} invalid')
        else:completions.append(item)
    if set(catalog_resources)!=set(reads):g.append('every captured resource catalog item requires a reviewed read')
    if set(catalog_prompts)!=set(gets):g.append('every captured prompt catalog item requires a reviewed render')
    observed_r={x.get('uri'):x for x in d.get('resources',[]) if isinstance(x,dict)} if isinstance(d.get('resources'),list) else {}
    orkeys={'uri','catalog_sha256','content_sha256','access_authorized','uri_validated','mime_validated','size_bytes','sensitivity','no_secret','treated_as_data','selected_by'}
    if set(observed_r)!=set(reads):g.append('resource observation set differs from captured reads')
    for uri,o in observed_r.items():
        item=reads.get(uri); size=sum(len(x['text'].encode()) for x in item['contents']) if item else -1
        if set(o)!=orkeys or o.get('catalog_sha256')!=csha(catalog_resources.get(uri)) or o.get('content_sha256')!=csha(item) or o.get('size_bytes')!=size or o.get('sensitivity') not in {'public','internal','confidential'} or not text(o.get('selected_by')) or any(o.get(k) is not True for k in ('access_authorized','uri_validated','mime_validated','no_secret','treated_as_data')):g.append(f'resource observation {uri} invalid')
    observed_t={x.get('uri_template'):x for x in d.get('resource_templates',[]) if isinstance(x,dict)} if isinstance(d.get('resource_templates'),list) else {}
    otkeys={'uri_template','catalog_sha256','arguments_validated','expansion_confined','completion_untrusted'}
    if set(observed_t)!=set(catalog_templates):g.append('resource template observation set differs from captured catalog')
    for uri,o in observed_t.items():
        if set(o)!=otkeys or o.get('catalog_sha256')!=csha(catalog_templates.get(uri)) or any(o.get(k) is not True for k in ('arguments_validated','expansion_confined','completion_untrusted')):g.append(f'resource template observation {uri} invalid')
    observed_p={x.get('name'):x for x in d.get('prompts',[]) if isinstance(x,dict)} if isinstance(d.get('prompts'),list) else {}
    opkeys={'name','catalog_sha256','arguments_sha256','render_sha256','user_selected','arguments_validated','output_validated','injection_reviewed','treated_as_data','authority_effect','embedded_resources_checked'}
    if set(observed_p)!=set(gets):g.append('prompt observation set differs from captured gets')
    for name,o in observed_p.items():
        item=gets.get(name)
        if set(o)!=opkeys or o.get('catalog_sha256')!=csha(catalog_prompts.get(name)) or o.get('arguments_sha256')!=csha(item.get('arguments') if item else None) or o.get('render_sha256')!=csha(item) or o.get('authority_effect')!='none' or any(o.get(k) is not True for k in ('user_selected','arguments_validated','output_validated','injection_reviewed','treated_as_data','embedded_resources_checked')):g.append(f'prompt observation {name} invalid')
    observed_c=d.get('completions',[]);ockeys={'reference_sha256','result_sha256','values_untrusted','selected_by_user','authority_effect'}
    if not isinstance(observed_c,list) or len(observed_c)!=len(completions):g.append('completion observation set differs from captured results');observed_c=[]
    for i,o in enumerate(observed_c):
        item=completions[i] if i<len(completions) else None
        if not isinstance(o,dict) or set(o)!=ockeys or o.get('reference_sha256')!=csha({'ref':item['ref'],'argument':item['argument']}) or o.get('result_sha256')!=csha(item) or o.get('authority_effect')!='none' or o.get('values_untrusted') is not True or o.get('selected_by_user') is not True:g.append(f'completion observation {i} invalid')
    tests=d.get('tests',{}); required_tests={'catalog_injection','catalog_removal','resource_uri_escape','resource_access_denied','resource_secret','resource_instruction','prompt_argument_injection','prompt_output_injection','embedded_resource_injection','completion_injection','list_change_drift','subscription_drift','passed'}
    if set(tests)!=required_tests or any(tests.get(k) is not True for k in required_tests):g.append('content security regression coverage incomplete')
    review=d.get('review',{});ra,rb=ts(review.get('reviewed_at')),ts(review.get('review_after'))
    if set(review)!={'owner','independent_reviewer','reviewed_at','review_after','approved','rollback'} or not all(text(review.get(k)) for k in ('owner','independent_reviewer','rollback')) or review.get('owner')==review.get('independent_reviewer') or not ra or not rb or rb<=ra or not isinstance(review.get('approved'),bool):g.append('independent content review invalid')
    dec=d.get('decision',{})
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'trust','quarantine','reject'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or any(not text(x) for x in dec.get('reasons',[])) or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    session_trusted=isinstance(session,dict) and session.get('receipt_kind')=='captured_session' and session.get('decision',{}).get('outcome')=='trust'
    if dec.get('outcome')=='trust' and (kind!='captured_content' or not session_trusted or review.get('approved') is not True or dec.get('unresolved_risks')):g.append('content trust requires captured trusted session, independent approval, and no unresolved risk')
    return e,g
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('--evidence-root',default='.');p.add_argument('--json',action='store_true');a=p.parse_args()
    path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d,Path(a.evidence_root),Path(__file__).with_name('validate-mcp-session.py'));ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('MCP content valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
