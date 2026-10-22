#!/usr/bin/env python3
'''Compile a redacted MCP JSON-RPC transcript into deterministic review evidence.'''
from __future__ import annotations
import argparse,hashlib,json,math,re,sys
from datetime import datetime
from pathlib import Path,PurePosixPath
from typing import Any
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import create_new_bytes,regular_input_file,safe_path
SENSITIVE_KEY=re.compile(r'(?i)(authorization|cookie|password|passwd|secret|token|api[-_]?key|private[-_]?key)')
SENSITIVE_VALUE=re.compile(r'(?i)(bearer\s+[a-z0-9._~+/-]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)')
HEX=re.compile(r'^[0-9a-f]{64}$'); LISTS={'tools/list':'tools','resources/list':'resources','resources/templates/list':'resourceTemplates','prompts/list':'prompts'}
OPS=set(LISTS)|{'resources/read','prompts/get','completion/complete'}
SUPPORTED_PROTOCOL_VERSIONS={'2025-06-18','2025-11-25'}  # initialize-handshake revisions
STATELESS_PROTOCOL_VERSIONS={'2026-07-28'}  # stateless core: per-request _meta version, no initialize or session
META_VERSION='io.modelcontextprotocol/protocolVersion';META_CAPS='io.modelcontextprotocol/clientCapabilities';META_CLIENT='io.modelcontextprotocol/clientInfo';META_SERVER='io.modelcontextprotocol/serverInfo';META_LOG='io.modelcontextprotocol/logLevel'
TASKS_EXTENSION='io.modelcontextprotocol/tasks'; CACHEABLE=set(LISTS)|{'resources/read','server/discover'}
CAPABILITY_FOR={'tools/list':'tools','resources/list':'resources','resources/templates/list':'resources','resources/read':'resources','prompts/list':'prompts','prompts/get':'prompts','completion/complete':'completions'}
def digest(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def jd(v:Any)->bytes:return (json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode()
def csha(v:Any)->str:return digest(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def stamp(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00'))
    except (AttributeError,ValueError):return None
def secret(v:Any)->bool:
    if isinstance(v,dict):return any(SENSITIVE_KEY.search(str(k)) or secret(x) for k,x in v.items())
    if isinstance(v,list):return any(secret(x) for x in v)
    return isinstance(v,str) and bool(SENSITIVE_VALUE.search(v))
def confined(root:Path,value:str)->Path:
    path=safe_path(value,root)
    if path is None:raise ValueError('path escapes evidence root or traverses a symlink')
    return path
def member(root:Path,base:Path,value:str)->Path:
    rel=PurePosixPath(value)
    if rel.is_absolute() or '..' in rel.parts:raise ValueError('path escapes evidence root')
    try:prefix=base.resolve().relative_to(root.resolve())
    except ValueError:raise ValueError('base escapes evidence root')
    path=safe_path((prefix/Path(*rel.parts)).as_posix(),root)
    if path is None:raise ValueError('path escapes evidence root or traverses a symlink')
    return path
def request_meta(m:dict)->dict:
    p=m.get('params');return p['_meta'] if isinstance(p,dict) and isinstance(p.get('_meta'),dict) else {}
def stateless_lifecycle(events:list,requests:dict,responses:dict,initialized:Any,errors:list[str])->dict[str,Any]:
    '''2026-07-28 rules: every request self-describes its version and capabilities; no handshake or session.'''
    ordered=sorted(requests.items(),key=lambda z:z[1][0]['seq']);versions=set();clients=[];servers=[];client_caps=set();extensions=set();deprecated=set();discover=None;cache={}
    if initialized:errors.append('initialize handshake in a stateless transcript: mixed protocol eras rejected, never downgraded')
    if any(x['session_id_sha256'] is not None for x in events):errors.append('stateless transcript cannot carry a session id: Mcp-Session-Id was removed in 2026-07-28')
    for rid,(x,m) in ordered:
        meta=request_meta(m);version=meta.get(META_VERSION);caps=meta.get(META_CAPS)
        if not isinstance(version,str) or not version:errors.append(f'request {rid} lacks _meta {META_VERSION}')
        else:versions.add(version)
        if not isinstance(caps,dict):errors.append(f'request {rid} lacks _meta {META_CAPS}')
        else:
            client_caps|=set(caps);deprecated|={k for k in ('roots','sampling') if k in caps}
            if isinstance(caps.get('extensions'),dict):extensions|=set(caps['extensions'])
        if META_LOG in meta:deprecated.add('logging')
        if META_CLIENT in meta:clients.append(meta[META_CLIENT])
        if x['transport']=='streamable_http' and x['protocol_version_header']!=version:errors.append(f'HTTP protocol version header invalid at {x["seq"]}')
        if m.get('method')=='server/discover':
            if discover:errors.append('server/discover repeated')
            discover=discover or (rid,x)
        elif m.get('method') not in OPS:errors.append(f'unsupported stateless operation: {m.get("method")}')
    if len(versions)>1:errors.append('mixed protocol versions in one transcript ('+', '.join(sorted(versions))+'): rejected, never downgraded')
    elif versions-STATELESS_PROTOCOL_VERSIONS:errors.append(f'protocol {min(versions)} is not a supported stateless revision: rejected, never downgraded')
    version=min(versions) if len(versions)==1 else None
    if events and events[0]['transport']=='stdio' and any(x['protocol_version_header'] is not None for x in events):errors.append('stdio transcript cannot carry HTTP version metadata')
    for rid,(x,m) in sorted(responses.items(),key=lambda z:z[1][0]['seq']):
        out=m.get('result');method=requests.get(rid,(None,{}))[1].get('method')
        if not isinstance(out,dict):continue
        kind=out.get('resultType')
        if kind is None:errors.append(f'result {rid} lacks resultType')
        elif kind=='input_required':errors.append(f'input_required result for {method}: multi-round-trip input requests need separate review; capture completed results only')
        elif kind=='task':errors.append(f'task result for {method} quarantined: the tasks extension is outside capture admission')
        elif kind!='complete':errors.append(f'result {rid} resultType unrecognized: {kind}')
        rmeta=out.get('_meta',{})
        if not isinstance(rmeta,dict):errors.append(f'result {rid} _meta invalid')
        elif META_SERVER in rmeta:servers.append(rmeta[META_SERVER])
        if method in CACHEABLE:
            ttl=out.get('ttlMs')
            if not isinstance(ttl,(int,float)) or isinstance(ttl,bool) or not math.isfinite(ttl) or ttl<0 or out.get('cacheScope') not in {'public','private'}:errors.append(f'cache metadata missing or invalid: {method}')
            else:cache.setdefault(method,[]).append({'ttl_ms':out['ttlMs'],'cache_scope':out['cacheScope']})
    for label,seen in (('client',clients),('server',servers)):
        if any(not isinstance(v,dict) or v!=seen[0] for v in seen):errors.append(f'{label} identity invalid or changes within transcript')
    caps=None
    if discover:
        out=responses.get(discover[0],(None,{}))[1].get('result')
        if isinstance(out,dict):
            caps=out.get('capabilities') if isinstance(out.get('capabilities'),dict) else None
            if caps is None:errors.append('server/discover capabilities invalid')
            if version and (not isinstance(out.get('supportedVersions'),list) or version not in out['supportedVersions']):errors.append('server/discover does not advertise the transcript protocol version')
            if out.get('instructions'):errors.append('server discovery instructions require separate quarantine review')
    if caps is not None:
        if 'logging' in caps:deprecated.add('logging')
        if isinstance(caps.get('extensions'),dict):extensions|=set(caps['extensions'])
        for _,(_,m) in ordered:
            if m.get('method') in CAPABILITY_FOR and CAPABILITY_FOR[m['method']] not in caps:errors.append(f'undiscovered capability used: {m["method"]}')
    if TASKS_EXTENSION in extensions:errors.append('tasks extension negotiated: quarantine it in an extension-specific harness')
    return {'protocol_version':version,'era':'stateless','transport':events[0]['transport'] if events else None,'client_info':clients[0] if clients else None,'server_info':servers[0] if servers else None,'capabilities':caps,'client_capabilities':sorted(client_caps),'deprecated_feature_exposure':sorted(deprecated),'discovered_seq':discover[1]['seq'] if discover else None,'cache':cache}
def compile_transcript(raw:bytes)->tuple[dict[str,Any],dict[str,Any],dict[str,Any]]:
    if len(raw)>10_000_000:raise ValueError('transcript exceeds 10 MB limit')
    errors=[];events=[]
    for n,line in enumerate(raw.splitlines(),1):
        if not line.strip():continue
        try:x=json.loads(line)
        except json.JSONDecodeError as ex:raise ValueError(f'line {n} JSON invalid: {ex}')
        keys={'seq','at','direction','transport','protocol_version_header','session_id_sha256','message'}
        if not isinstance(x,dict) or set(x)!=keys:errors.append(f'line {n} envelope invalid');continue
        if x['seq']!=len(events)+1 or not stamp(x['at']) or x['direction'] not in {'client_to_server','server_to_client'} or x['transport'] not in {'streamable_http','stdio'} or not isinstance(x['message'],dict) or x['message'].get('jsonrpc')!='2.0' or secret(x):errors.append(f'line {n} identity or redaction invalid')
        events.append(x)
        if len(events)>10_000:raise ValueError('transcript exceeds 10000-message limit')
    if not events:errors.append('transcript empty')
    if len({x['transport'] for x in events})>1:errors.append('transport changes within session')
    if any(stamp(events[i]['at'])<stamp(events[i-1]['at']) for i in range(1,len(events))):errors.append('timestamps not monotonic')
    requests={};responses={};initialized=None;init_req=None;init_res=None
    for x in events:
        m=x['message'];direction=x['direction']
        if 'method' in m and 'id' in m:
            if direction!='client_to_server' or set(m)-{'jsonrpc','id','method','params'}:errors.append(f'request {m.get("id")} invalid')
            elif m['id'] in requests:errors.append(f'duplicate request id {m["id"]}')
            else:requests[m['id']]=(x,m)
        elif 'method' in m:
            if set(m)-{'jsonrpc','method','params'}:errors.append(f'notification {m.get("method")} invalid')
            if m.get('method')=='notifications/initialized':initialized=x
            elif direction=='server_to_client':errors.append(f'capture invalidated by server notification: {m.get("method")}')
            else:errors.append(f'unsupported client notification: {m.get("method")}')
        elif 'id' in m:
            if direction!='server_to_client' or (('result' in m)==('error' in m)) or set(m)-{'jsonrpc','id','result','error'}:errors.append(f'response {m.get("id")} invalid')
            elif m['id'] in responses:errors.append(f'duplicate response id {m["id"]}')
            else:responses[m['id']]=(x,m)
        else:errors.append(f'message {x["seq"]} is not request, response, or notification')
    for rid in set(requests)|set(responses):
        if rid not in requests or rid not in responses:errors.append(f'request/response pair incomplete: {rid}')
        elif responses[rid][0]['seq']<requests[rid][0]['seq']:errors.append(f'response precedes request: {rid}')
    stateless=not any(m.get('method')=='initialize' for _,m in requests.values()) and any(META_VERSION in request_meta(m) for _,m in requests.values())
    if stateless:smeta=stateless_lifecycle(events,requests,responses,initialized,errors)
    else:
        init=[(rid,x,m) for rid,(x,m) in requests.items() if m.get('method')=='initialize']
        if len(init)!=1:errors.append('exactly one initialize request required')
        else:
            rid,init_req,im=init[0];init_res=responses.get(rid,(None,{}))[0];result=responses.get(rid,(None,{}))[1].get('result',{})
            if init_req['seq']!=1 or not init_res or not initialized or not (init_req['seq']<init_res['seq']<initialized['seq']):errors.append('initialize lifecycle order invalid')
            requested=im.get('params',{}).get('protocolVersion');negotiated=result.get('protocolVersion')
            if requested in STATELESS_PROTOCOL_VERSIONS or negotiated in STATELESS_PROTOCOL_VERSIONS:errors.append('protocol 2026-07-28 is stateless and has no initialize handshake: rejected, never downgraded')
            elif not requested or requested!=negotiated or negotiated not in SUPPORTED_PROTOCOL_VERSIONS:errors.append('protocol version negotiation invalid or unsupported')
            if {request_meta(m)[META_VERSION] for _,m in requests.values() if META_VERSION in request_meta(m)}-{negotiated}:errors.append('per-request _meta protocol version conflicts with the initialize handshake: mixed protocol eras rejected, never downgraded')
            if result.get('instructions'):errors.append('server initialization instructions require separate quarantine review')
        init_seq=initialized['seq'] if initialized else 10**9
        for _,(x,m) in requests.items():
            if m.get('method')!='initialize' and (x['seq']<=init_seq or m.get('method') not in OPS):errors.append(f'operation before initialization or unsupported: {m.get("method")}')
        result=responses.get(init[0][0],(None,{}))[1].get('result',{}) if len(init)==1 else {};caps=result.get('capabilities',{});negotiated=set(caps) if isinstance(caps,dict) else set()
        for _,(_,m) in requests.items():
            if m.get('method') in CAPABILITY_FOR and CAPABILITY_FOR[m['method']] not in negotiated:errors.append(f'unnegotiated capability used: {m["method"]}')
        transport=events[0]['transport'] if events else None;session_hash=init_res.get('session_id_sha256') if init_res else None;version=result.get('protocolVersion')
        if transport=='streamable_http':
            if not HEX.fullmatch(str(session_hash or '')):errors.append('initialization response lacks hashed session id')
            for x in events:
                if x['seq']>init_res['seq'] and (x['session_id_sha256']!=session_hash or (x['direction']=='client_to_server' and x['protocol_version_header']!=version)):errors.append(f'HTTP session/version header invalid at {x["seq"]}')
        elif any(x['protocol_version_header'] is not None or x['session_id_sha256'] is not None for x in events):errors.append('stdio transcript cannot carry HTTP session metadata')
    pages={k:[] for k in LISTS};reads=[];gets=[];completions=[]
    for rid,(x,m) in sorted(requests.items(),key=lambda z:z[1][0]['seq']):
        method=m['method'];answer=responses.get(rid,(None,{}))[1]
        if 'error' in answer:errors.append(f'captured request failed: {method}');continue
        out=answer.get('result',{})
        if not isinstance(out,dict):errors.append(f'captured result invalid: {method}');continue
        if method in LISTS:pages[method].append((m.get('params',{}),out))
        elif method=='resources/read':reads.append({'uri':m.get('params',{}).get('uri'),'contents':out.get('contents')})
        elif method=='prompts/get':gets.append({'name':m.get('params',{}).get('name'),'arguments':m.get('params',{}).get('arguments',{}),'description':out.get('description'),'messages':out.get('messages')})
        elif method=='completion/complete':
            comp=out.get('completion',{});completions.append({'ref':m.get('params',{}).get('ref'),'argument':m.get('params',{}).get('argument'),'values':comp.get('values'),'total':comp.get('total'),'hasMore':comp.get('hasMore')})
    pagination={};aggregated={}
    for method,key in LISTS.items():
        chain=pages[method];prior=None;items=[];cursor_hashes=[];seen=set()
        if not chain:errors.append(f'missing list capture: {method}');continue
        for i,(params,out) in enumerate(chain):
            cursor=params.get('cursor') if isinstance(params,dict) else None
            if cursor!=prior:errors.append(f'pagination cursor chain invalid: {method} page {i+1}')
            values=out.get(key);nxt=out.get('nextCursor')
            if not isinstance(values,list):errors.append(f'pagination result invalid: {method} page {i+1}');values=[]
            items.extend(values)
            if nxt is not None:
                if not isinstance(nxt,str) or not nxt or nxt in seen:errors.append(f'pagination nextCursor invalid: {method}')
                seen.add(nxt)
                cursor_hashes.append(csha(nxt))
            prior=nxt
        if prior is not None:errors.append(f'pagination incomplete: {method}')
        aggregated[key]=items;pagination[method]={'pages':len(chain),'complete':prior is None,'cursor_sha256':cursor_hashes}
    if errors:raise ValueError('; '.join(errors))
    tools={'tools':aggregated['tools']}
    content={'resources':aggregated['resources'],'resourceTemplates':aggregated['resourceTemplates'],'prompts':aggregated['prompts'],'resourceReads':reads,'promptGets':gets,'completions':completions}
    if stateless:meta={**smeta,'message_count':len(events),'request_count':len(requests),'pagination':pagination}
    else:meta={'protocol_version':version,'transport':transport,'session_id_sha256':session_hash,'client_info':requests[init[0][0]][1]['params'].get('clientInfo'),'server_info':result.get('serverInfo'),'capabilities':caps,'message_count':len(events),'request_count':len(requests),'pagination':pagination,'initialized_seq':initialized['seq']}
    return tools,content,meta
def build_manifest(transcript_path:str,transcript_raw:bytes,tools_path:str,tools:dict,content_path:str,content:dict,meta:dict)->dict:
    return {'schema_version':1,'receipt_kind':'compiled_transcript','transcript':{'path':transcript_path,'sha256':digest(transcript_raw),'redacted':True},'protocol':meta,'outputs':{'tools_list':{'path':tools_path,'canonical_sha256':csha(tools)},'server_content':{'path':content_path,'canonical_sha256':csha(content)}},'compiler':{'name':'engineer-compile-mcp-transcript','schema_version':1}}
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('transcript',nargs='?');p.add_argument('--output-dir');p.add_argument('--check-manifest');p.add_argument('--evidence-root',default='.');p.add_argument('--json',action='store_true');a=p.parse_args();root=Path(a.evidence_root)
    try:
        if a.check_manifest:
            mp=confined(root,a.check_manifest);manifest=json.loads(mp.read_bytes());t=manifest['transcript'];tp=member(root,mp.parent,t['path']);raw=tp.read_bytes()
            tools,content,meta=compile_transcript(raw);expected=build_manifest(t['path'],raw,manifest['outputs']['tools_list']['path'],tools,manifest['outputs']['server_content']['path'],content,meta)
            if manifest!=expected:raise ValueError('manifest differs from deterministic transcript compilation')
            for label,obj in [('tools_list',tools),('server_content',content)]:
                op=member(root,mp.parent,manifest['outputs'][label]['path'])
                if json.loads(op.read_bytes())!=obj:raise ValueError(f'{label} output differs from deterministic compilation')
            out={'valid':True,'manifest_sha256':digest(mp.read_bytes())};print(json.dumps(out,indent=2) if a.json else 'MCP capture manifest valid');return 0
        if not a.transcript or not a.output_dir:raise ValueError('transcript and --output-dir are required')
        tp=regular_input_file(a.transcript)
        if tp is None:raise ValueError('transcript must be a regular file, not a symlink')
        raw=tp.read_bytes();tools,content,meta=compile_transcript(raw);od=Path(a.output_dir);od.mkdir(parents=True,exist_ok=False)
        create_new_bytes(od/'transcript.jsonl',raw);create_new_bytes(od/'tools-list.json',jd(tools));create_new_bytes(od/'server-content.json',jd(content));manifest=build_manifest('transcript.jsonl',raw,'tools-list.json',tools,'server-content.json',content,meta);create_new_bytes(od/'capture-manifest.json',jd(manifest));print(json.dumps(manifest,indent=2) if a.json else str(od/'capture-manifest.json'));return 0
    except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
