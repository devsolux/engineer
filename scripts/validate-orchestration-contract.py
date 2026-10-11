#!/usr/bin/env python3
'''Validate a bounded multi-agent orchestration contract.'''

from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

IDENT=re.compile(r'^[a-z][a-z0-9_-]{1,63}$')
TOOLS={'read','search','edit','shell','browser','network','message','deploy','money','permission_admin'}
DANGEROUS={'network','message','deploy','money','permission_admin'}

def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def ident(v:Any)->bool:return isinstance(v,str) and bool(IDENT.fullmatch(v))
def lane(v:Any)->bool:
    if not text(v): return False
    p=PurePosixPath(v)
    return not p.is_absolute() and '..' not in p.parts and '.' not in p.parts
def positive(v:Any)->bool:return isinstance(v,(int,float)) and not isinstance(v,bool) and v>0

def validate(d:Any)->tuple[list[str],list[str]]:
    e=[];g=[]
    root={'schema_version','receipt_kind','goal','limits','agents','delegations','lanes','join','failure_policy','trace_policy','synthesis','review'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=root:e.append(f'root keys must be exactly {sorted(root)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    if d.get('receipt_kind') not in {'illustrative_fixture','captured_contract'}:e.append('invalid receipt_kind')
    goal=d.get('goal',{})
    if set(goal)!={'id','summary','requirements','multi_agent_justification'}:e.append('goal keys invalid')
    if not ident(goal.get('id')) or not text(goal.get('summary')) or not isinstance(goal.get('requirements'),list) or not goal.get('requirements') or any(not ident(x) for x in goal.get('requirements',[])) or not text(goal.get('multi_agent_justification')):e.append('goal content invalid')
    limits=d.get('limits',{})
    lkeys={'max_agents','max_depth','max_fanout','max_steps','max_cost_usd','max_wall_seconds','max_retries_per_task','no_progress_limit','synthesis_reserve_cost_usd'}
    if set(limits)!=lkeys or any(not positive(limits.get(k)) for k in lkeys):e.append('limits invalid')
    agents=d.get('agents',[]); amap={}; roots=[]
    akeys={'id','role','parent_id','task','requirements','tools','denied_tools','destinations','secret_classes','approval_class','revocation_handle','budget','output_schema','stop_conditions'}
    if not isinstance(agents,list) or len(agents)<2:e.append('agents must contain at least two entries');agents=[]
    for i,a in enumerate(agents):
        if not isinstance(a,dict) or set(a)!=akeys:e.append(f'agent {i} keys invalid');continue
        aid=a.get('id')
        if not ident(aid) or aid in amap:e.append(f'agent {i} id invalid or duplicate');continue
        amap[aid]=a
        if a.get('parent_id') is None:roots.append(aid)
        if not all(text(a.get(k)) for k in ('role','task','approval_class','revocation_handle')):e.append(f'agent {aid} text fields invalid')
        req=a.get('requirements');
        if not isinstance(req,list) or not req or not set(req).issubset(set(goal.get('requirements',[]))):e.append(f'agent {aid} requirements invalid')
        tools=a.get('tools');denied=a.get('denied_tools')
        if not isinstance(tools,list) or any(x not in TOOLS for x in tools) or len(tools)!=len(set(tools)):e.append(f'agent {aid} tools invalid')
        if not isinstance(denied,list) or any(x not in TOOLS for x in denied) or set(tools or [])&set(denied or []):e.append(f'agent {aid} denied_tools invalid')
        if set(tools or [])&DANGEROUS and a.get('approval_class')=='none':g.append(f'agent {aid} dangerous tools lack approval class')
        for k in ('destinations','secret_classes','stop_conditions'):
            if not isinstance(a.get(k),list) or any(not text(x) for x in a.get(k,[])):e.append(f'agent {aid} {k} invalid')
        if not isinstance(a.get('output_schema'),dict) or not a.get('output_schema'):e.append(f'agent {aid} output_schema required')
        budget=a.get('budget',{})
        if set(budget)!={'max_steps','max_cost_usd','max_wall_seconds','max_descendants'} or any(not positive(budget.get(k)) for k in budget):e.append(f'agent {aid} budget invalid')
    if len(roots)!=1:g.append('exactly one root agent required')
    if len(amap)>limits.get('max_agents',0):g.append('agent count exceeds global limit')
    covered=set().union(*(set(a.get('requirements',[])) for a in amap.values())) if amap else set()
    if covered!=set(goal.get('requirements',[])):g.append('every goal requirement must be assigned')
    for aid,a in amap.items():
        p=a.get('parent_id')
        if p is not None and p not in amap:e.append(f'agent {aid} parent missing')
        if p==aid:e.append(f'agent {aid} cannot parent itself')
        if a.get('budget',{}).get('max_wall_seconds',0)>limits.get('max_wall_seconds',0):g.append(f'agent {aid} wall budget exceeds global limit')

    edges=d.get('delegations',[]); pairs=set(); children={x:[] for x in amap}
    dkeys={'from','to','task_id','input_refs','context_allowlist','authority_tools','output_ref','evidence_required','approval_required'}
    if not isinstance(edges,list) or not edges:e.append('delegations required');edges=[]
    for i,x in enumerate(edges):
        if not isinstance(x,dict) or set(x)!=dkeys:e.append(f'delegation {i} keys invalid');continue
        f,t=x.get('from'),x.get('to')
        if f not in amap or t not in amap or (f,t) in pairs:e.append(f'delegation {i} endpoints invalid or duplicate');continue
        pairs.add((f,t));children[f].append(t)
        if amap[t].get('parent_id')!=f:g.append(f'delegation {f}->{t} conflicts with parent_id')
        if not ident(x.get('task_id')) or not all(isinstance(x.get(k),list) and all(text(v) for v in x.get(k,[])) for k in ('input_refs','context_allowlist','authority_tools','evidence_required')) or not text(x.get('output_ref')) or not isinstance(x.get('approval_required'),bool):e.append(f'delegation {i} payload invalid')
        if not set(x.get('authority_tools',[])).issubset(set(amap[f].get('tools',[]))) or not set(x.get('authority_tools',[])).issubset(set(amap[t].get('tools',[]))):g.append(f'delegation {f}->{t} does not attenuate authority')
        if set(x.get('authority_tools',[]))!=set(amap[t].get('tools',[])):g.append(f'delegation {f}->{t} does not account for every child tool')
        if set(x.get('authority_tools',[]))&DANGEROUS and not x.get('approval_required'):g.append(f'delegation {f}->{t} dangerous authority lacks approval')
    color={x:0 for x in amap}
    def visit(n:str,depth:int)->None:
        if color[n]==1:g.append('delegation graph contains a cycle');return
        if color[n]==2:return
        color[n]=1
        if depth>limits.get('max_depth',0):g.append('delegation depth exceeds limit')
        if len(children[n])>limits.get('max_fanout',0):g.append(f'fanout exceeds limit at {n}')
        if len(children[n])>amap[n].get('budget',{}).get('max_descendants',0):g.append(f'descendant allocation exceeds agent budget at {n}')
        for c in children[n]:visit(c,depth+1)
        color[n]=2
    for r in roots:visit(r,1)
    if any(v==0 for v in color.values()):g.append('all agents must be reachable from root')
    total_cost=sum(float(a.get('budget',{}).get('max_cost_usd',0)) for a in amap.values())
    total_steps=sum(float(a.get('budget',{}).get('max_steps',0)) for a in amap.values())
    if total_cost>float(limits.get('max_cost_usd',0)):g.append('agent cost allocations exceed global budget')
    if total_steps>float(limits.get('max_steps',0)):g.append('agent step allocations exceed global budget')
    if roots and amap[roots[0]].get('budget',{}).get('max_cost_usd',0)<limits.get('synthesis_reserve_cost_usd',0):g.append('root budget does not preserve synthesis reserve')

    lanes=d.get('lanes',[]);writes={};lane_agents=[]
    if not isinstance(lanes,list) or len(lanes)!=len(amap):e.append('one lane declaration per agent required');lanes=[]
    for i,x in enumerate(lanes):
        if not isinstance(x,dict) or set(x)!={'agent_id','read','write','worktree','browser_profile','artifact_dir'}:e.append(f'lane {i} keys invalid');continue
        aid=x.get('agent_id')
        lane_agents.append(aid)
        if aid not in amap:e.append(f'lane {i} agent invalid')
        for k in ('read','write'):
            if not isinstance(x.get(k),list) or any(not lane(v) for v in x.get(k,[])):e.append(f'lane {i} {k} invalid')
        for k in ('worktree','browser_profile','artifact_dir'):
            if not lane(x.get(k)):e.append(f'lane {i} {k} invalid')
        for w in x.get('write',[]):
            if w in writes and writes[w]!=aid:g.append(f'write lane {w} shared by {writes[w]} and {aid}')
            writes[w]=aid
    if set(lane_agents)!=set(amap) or len(lane_agents)!=len(set(lane_agents)):g.append('lane declarations must cover each agent exactly once')
    join=d.get('join',{})
    if set(join)!={'strategy','quorum','timeout_seconds','on_missing','conflict_resolution','cancel_remaining'} or join.get('strategy') not in {'all','quorum','first_valid','best_scored'} or not positive(join.get('timeout_seconds')) or join.get('on_missing') not in {'fail','partial_with_disclosure','escalate'} or not text(join.get('conflict_resolution')) or not isinstance(join.get('cancel_remaining'),bool):e.append('join invalid')
    if join.get('strategy')=='quorum' and (not isinstance(join.get('quorum'),int) or join['quorum']<2 or join['quorum']>len(amap)-1):g.append('quorum invalid')
    fp=d.get('failure_policy',{})
    if set(fp)!={'retry_only_transient','idempotency_required','circuit_breakers','heartbeat_seconds','lease_seconds','cancel_descendants','orphan_detection','human_escalation'} or fp.get('retry_only_transient') is not True or fp.get('idempotency_required') is not True or not isinstance(fp.get('circuit_breakers'),list) or not fp.get('circuit_breakers') or any(not text(x) for x in fp.get('circuit_breakers',[])) or not positive(fp.get('heartbeat_seconds')) or not positive(fp.get('lease_seconds')) or fp.get('lease_seconds',0)<=fp.get('heartbeat_seconds',0) or fp.get('cancel_descendants') is not True or fp.get('orphan_detection') is not True or not text(fp.get('human_escalation')):g.append('failure policy incomplete')
    tp=d.get('trace_policy',{})
    if set(tp)!={'workflow_trace','parented_spans','events','include_sensitive_data','redaction','artifact_hashes','retention'} or tp.get('workflow_trace') is not True or tp.get('parented_spans') is not True or not isinstance(tp.get('events'),list) or not {'agent','handoff','tool','guardrail','join','cancel','approval'}.issubset(set(tp.get('events',[]))) or tp.get('include_sensitive_data') is not False or not text(tp.get('redaction')) or tp.get('artifact_hashes') is not True or not text(tp.get('retention')):g.append('trace policy incomplete or sensitive by default')
    syn=d.get('synthesis',{})
    if set(syn)!={'agent_id','provenance_required','conflicts_disclosed','missing_results_disclosed','independent_verification','final_evidence_ref'} or syn.get('agent_id') not in amap or syn.get('provenance_required') is not True or syn.get('conflicts_disclosed') is not True or syn.get('missing_results_disclosed') is not True or syn.get('independent_verification') is not True or not text(syn.get('final_evidence_ref')):g.append('synthesis policy incomplete')
    review=d.get('review',{})
    if set(review)!={'owner','independent_reviewer','approved','review_after','rollback'} or not all(text(review.get(k)) for k in ('owner','independent_reviewer','review_after','rollback')) or review.get('owner')==review.get('independent_reviewer') or not isinstance(review.get('approved'),bool):g.append('independent review declaration required')
    if d.get('receipt_kind')=='captured_contract' and review.get('approved') is not True:g.append('captured contract requires approval')
    if d.get('receipt_kind')=='illustrative_fixture' and review.get('approved') is True:g.append('illustrative fixture cannot authorize execution')
    return e,g

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('contract');p.add_argument('--json',action='store_true');a=p.parse_args()
    path=regular_input_file(a.contract)
    if path is None:print('contract must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d);ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('orchestration contract valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
