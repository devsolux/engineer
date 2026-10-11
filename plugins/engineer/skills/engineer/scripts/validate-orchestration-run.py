#!/usr/bin/env python3
'''Validate observed multi-agent execution against its orchestration contract.'''

from __future__ import annotations
import argparse, hashlib, importlib.util, json, re, sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX=re.compile(r'^[0-9a-f]{64}$')
KINDS={'agent','handoff','tool','guardrail','join','cancel','approval','synthesis','verify'}
sys.dont_write_bytecode=True
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else None
    except ValueError:return None
def rel(v:Any):
    if not text(v):return None
    p=PurePosixPath(v);return None if p.is_absolute() or '..' in p.parts or '.' in p.parts else p
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def contract_validator(path:Path):
    script=Path(__file__).with_name('validate-orchestration-contract.py')
    spec=importlib.util.spec_from_file_location('orchestration_contract',script)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    data=json.loads(path.read_text(encoding='utf-8'));errors,gates=mod.validate(data)
    return data,errors+gates

def validate(d:Any, receipt:Path)->tuple[list[str],list[str]]:
    e=[];g=[]
    keys={'schema_version','receipt_kind','run','trace','artifacts','workers','spans','join','synthesis','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=keys:e.append(f'root keys must be exactly {sorted(keys)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_run'}:e.append('invalid receipt_kind')
    run=d.get('run',{});rkeys={'id','contract_path','contract_sha256','started_at','ended_at','environment','infrastructure_errors'}
    if set(run)!=rkeys:e.append('run keys invalid')
    cp=rel(run.get('contract_path'));contract={}
    if not text(run.get('id')) or not cp or not HEX.fullmatch(str(run.get('contract_sha256',''))) or not ts(run.get('started_at')) or not ts(run.get('ended_at')) or (ts(run.get('started_at')) and ts(run.get('ended_at')) and ts(run['ended_at'])<ts(run['started_at'])) or not text(run.get('environment')) or not isinstance(run.get('infrastructure_errors'),list):e.append('run identity invalid')
    cpath=receipt.parent/cp if cp else None
    if not cpath or not cpath.is_file():e.append('contract path missing')
    elif sha(cpath)!=run.get('contract_sha256'):e.append('contract hash mismatch')
    else:
        try:contract,issues=contract_validator(cpath)
        except (OSError,json.JSONDecodeError,AttributeError) as ex:e.append(f'contract unreadable: {ex}')
        else:
            if issues:g.append(f'bound contract is invalid: {issues}')
    trace=d.get('trace',{});tkeys={'trace_id','workflow_name','root_span_id','include_sensitive_data','redaction_applied','complete'}
    if set(trace)!=tkeys or not all(text(trace.get(k)) for k in ('trace_id','workflow_name','root_span_id')) or trace.get('include_sensitive_data') is not False or trace.get('redaction_applied') is not True or trace.get('complete') is not True:g.append('trace identity, redaction, or completeness invalid')

    arts=d.get('artifacts',[]);amap={}
    if not isinstance(arts,list) or not arts:e.append('artifacts required');arts=[]
    for i,a in enumerate(arts):
        if not isinstance(a,dict) or set(a)!={'id','producer_agent','path','sha256','kind','captured_at','redacted'}:e.append(f'artifact {i} keys invalid');continue
        aid=a.get('id');p=rel(a.get('path'))
        if not text(aid) or aid in amap or not p or not HEX.fullmatch(str(a.get('sha256',''))) or a.get('kind') not in {'worker_output','trace','final_output','verification'} or not ts(a.get('captured_at')) or a.get('redacted') is not True:e.append(f'artifact {i} metadata invalid');continue
        fp=receipt.parent/p
        if not fp.is_file() or sha(fp)!=a['sha256']:e.append(f'artifact {aid} missing or hash mismatch')
        amap[aid]=a

    agents={a.get('id'):a for a in contract.get('agents',[]) if isinstance(a,dict)}
    lanes={x.get('agent_id'):x for x in contract.get('lanes',[]) if isinstance(x,dict)}
    workers=d.get('workers',[]);wmap={}
    wkeys={'agent_id','parent_id','lease_id','heartbeats','lease_released','started_at','ended_at','outcome','steps','cost_usd','retries','output_artifact_id','cancelled_descendants'}
    if not isinstance(workers,list):e.append('workers must be an array');workers=[]
    for i,w in enumerate(workers):
        if not isinstance(w,dict) or set(w)!=wkeys:e.append(f'worker {i} keys invalid');continue
        aid=w.get('agent_id')
        if aid not in agents or aid in wmap:e.append(f'worker {i} agent invalid or duplicate');continue
        wmap[aid]=w
        if w.get('parent_id')!=agents[aid].get('parent_id') or not text(w.get('lease_id')) or not isinstance(w.get('heartbeats'),int) or w.get('heartbeats')<1 or w.get('lease_released') is not True or not ts(w.get('started_at')) or not ts(w.get('ended_at')) or w.get('outcome') not in {'success','failed','cancelled','infrastructure_error'} or not isinstance(w.get('steps'),int) or w.get('steps')<0 or not isinstance(w.get('cost_usd'),(int,float)) or isinstance(w.get('cost_usd'),bool) or w.get('cost_usd')<0 or not isinstance(w.get('retries'),int) or w.get('retries')<0 or not isinstance(w.get('cancelled_descendants'),list):e.append(f'worker {aid} runtime fields invalid')
        budget=agents[aid].get('budget',{})
        if w.get('steps',0)>budget.get('max_steps',0) or w.get('cost_usd',0)>budget.get('max_cost_usd',0) or w.get('retries',0)>contract.get('limits',{}).get('max_retries_per_task',0):g.append(f'worker {aid} exceeded budget')
        out=w.get('output_artifact_id')
        if w.get('outcome')=='success' and (out not in amap or amap[out].get('producer_agent')!=aid):g.append(f'worker {aid} success lacks its output artifact')
    if set(wmap)!=set(agents):g.append('workers must cover every contracted agent exactly once')
    if sum(w.get('steps',0) for w in workers if isinstance(w,dict))>contract.get('limits',{}).get('max_steps',0) or sum(w.get('cost_usd',0) for w in workers if isinstance(w,dict))>contract.get('limits',{}).get('max_cost_usd',0):g.append('global runtime budget exceeded')

    spans=d.get('spans',[]);smap={};handoffs=set();kinds=set();tool_counts={a:0 for a in agents}
    skeys={'seq','span_id','parent_span_id','kind','agent_id','task_id','started_at','ended_at','status','tool','destination','write_lane','approval','cost_usd','steps','retry','artifact_ids','redacted'}
    if not isinstance(spans,list) or not spans:e.append('spans required');spans=[]
    for i,s in enumerate(spans):
        if not isinstance(s,dict) or set(s)!=skeys:e.append(f'span {i} keys invalid');continue
        sid=s.get('span_id');kindx=s.get('kind');aid=s.get('agent_id')
        if s.get('seq')!=i+1 or not text(sid) or sid in smap or kindx not in KINDS or aid not in agents or not ts(s.get('started_at')) or not ts(s.get('ended_at')) or s.get('status') not in {'ok','error','cancelled'} or not isinstance(s.get('cost_usd'),(int,float)) or isinstance(s.get('cost_usd'),bool) or s.get('cost_usd')<0 or not isinstance(s.get('steps'),int) or s.get('steps')<0 or not isinstance(s.get('retry'),int) or s.get('retry')<0 or not isinstance(s.get('artifact_ids'),list) or any(x not in amap for x in s.get('artifact_ids',[])) or s.get('redacted') is not True:e.append(f'span {i} metadata invalid');continue
        smap[sid]=s;kinds.add(kindx)
        parent=s.get('parent_span_id')
        if sid==trace.get('root_span_id'):
            if parent is not None:g.append('root span must not have a parent')
        elif parent not in smap:g.append(f'span {sid} parent must precede it in the same trace')
        if kindx=='handoff':
            target=s.get('destination');handoffs.add((aid,target))
            if (aid,target) not in {(x.get('from'),x.get('to')) for x in contract.get('delegations',[])}:g.append(f'undeclared handoff {aid}->{target}')
        if kindx=='tool':
            tool_counts[aid]+=1;tool=s.get('tool');dest=s.get('destination');wl=s.get('write_lane')
            if tool not in agents[aid].get('tools',[]):g.append(f'agent {aid} used undeclared tool {tool}')
            if dest is not None and dest not in agents[aid].get('destinations',[]):g.append(f'agent {aid} used undeclared destination {dest}')
            if wl is not None and wl not in lanes.get(aid,{}).get('write',[]):g.append(f'agent {aid} wrote outside its lane: {wl}')
            if agents[aid].get('approval_class')!='none' and tool in {'edit','shell','browser','network','message','deploy','money','permission_admin'} and s.get('approval')!=agents[aid].get('approval_class'):g.append(f'agent {aid} tool span lacks contracted approval')
        if s.get('retry',0)>contract.get('limits',{}).get('max_retries_per_task',0):g.append(f'span {sid} retry exceeds limit')
    required=set(contract.get('trace_policy',{}).get('events',[]))|{'synthesis','verify'}
    if not required.issubset(kinds):g.append(f'trace missing required span kinds: {sorted(required-kinds)}')
    expected={(x.get('from'),x.get('to')) for x in contract.get('delegations',[])}
    if handoffs!=expected:g.append('observed handoffs do not exactly match contract')

    join=d.get('join',{});jkeys={'strategy','participants','completed','timed_out','missing_agents','conflicts','cancelled_agents','span_id'}
    child_agents={a for a,x in agents.items() if x.get('parent_id') is not None}
    if set(join)!=jkeys or join.get('strategy')!=contract.get('join',{}).get('strategy') or set(join.get('participants',[]))!=child_agents or join.get('completed') is not True or not isinstance(join.get('timed_out'),bool) or not isinstance(join.get('missing_agents'),list) or any(x not in child_agents for x in join.get('missing_agents',[])) or not isinstance(join.get('conflicts'),list) or not isinstance(join.get('cancelled_agents'),list) or join.get('span_id') not in smap or smap.get(join.get('span_id'),{}).get('kind')!='join':g.append('observed join is inconsistent with contract or trace')
    if join.get('missing_agents') and contract.get('join',{}).get('on_missing')=='fail' and d.get('decision',{}).get('outcome')=='pass':g.append('run passed despite fail-on-missing join')

    syn=d.get('synthesis',{});sykeys={'agent_id','span_id','final_artifact_id','provenance','conflicts_disclosed','missing_results_disclosed','verifier','verification_artifact_id','verification_passed'}
    if set(syn)!=sykeys or syn.get('agent_id')!=contract.get('synthesis',{}).get('agent_id') or syn.get('span_id') not in smap or smap.get(syn.get('span_id'),{}).get('kind')!='synthesis' or syn.get('final_artifact_id') not in amap or amap.get(syn.get('final_artifact_id'),{}).get('kind')!='final_output' or not isinstance(syn.get('provenance'),dict) or set(syn.get('provenance',{}))!=set(contract.get('goal',{}).get('requirements',[])) or any(not isinstance(v,list) or not v or any(x not in amap for x in v) for v in syn.get('provenance',{}).values()) or syn.get('conflicts_disclosed') is not True or syn.get('missing_results_disclosed') is not True or not text(syn.get('verifier')) or syn.get('verifier')==syn.get('agent_id') or syn.get('verification_artifact_id') not in amap or syn.get('verification_passed') is not True:g.append('synthesis provenance or independent verification invalid')
    review=d.get('review',{})
    if set(review)!={'reviewer','trace_sample_reviewed','artifacts_reviewed','approved','notes'} or not text(review.get('reviewer')) or review.get('reviewer') in {syn.get('agent_id'),syn.get('verifier')} or review.get('trace_sample_reviewed') is not True or review.get('artifacts_reviewed') is not True or not isinstance(review.get('approved'),bool) or not text(review.get('notes')):g.append('independent runtime review invalid')
    dec=d.get('decision',{})
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'pass','fail','infrastructure_error'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or any(not text(x) for x in dec.get('reasons',[])) or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    if dec.get('outcome')=='pass':
        if kind!='captured_run':g.append('only a captured_run may pass')
        if run.get('infrastructure_errors') or dec.get('unresolved_risks') or review.get('approved') is not True:g.append('passing run requires no infrastructure errors or unresolved risks and approved review')
    return e,g

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('receipt',type=Path);p.add_argument('--json',action='store_true');a=p.parse_args();path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d,path);ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('orchestration run valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
