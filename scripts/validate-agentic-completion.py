#!/usr/bin/env python3
'''Validate agent completion against contract-defined oracles and captured local evidence.'''
from __future__ import annotations
import argparse,hashlib,json,subprocess,sys
from datetime import datetime
from pathlib import Path,PurePosixPath
from typing import Any
sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file
HEX=lambda v:isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def sha(v:bytes)->str:return hashlib.sha256(v).hexdigest()
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00'))
    except (AttributeError,ValueError):return None
def confined(root:Path,value:Any)->Path:
    if not text(value):raise ValueError('path missing')
    rel=PurePosixPath(value)
    if rel.is_absolute() or '..' in rel.parts:raise ValueError('path escapes evidence root')
    path=(root/Path(*rel.parts)).resolve();path.relative_to(root.resolve());return path
def load_bound(root:Path,path:Any,digest:Any,label:str,e:list[str],g:list[str]):
    try:p=confined(root,path);raw=p.read_bytes()
    except (ValueError,OSError) as ex:g.append(f'{label} unavailable: {ex}');return None,None
    if not HEX(digest) or sha(raw)!=digest:g.append(f'{label} digest mismatch')
    try:return json.loads(raw),p
    except json.JSONDecodeError as ex:e.append(f'{label} JSON invalid: {ex}');return None,p
def canonical(script:Path,args:list[str])->bool:
    try:r=subprocess.run([sys.executable,str(script),*args],capture_output=True,text=True,timeout=15);return r.returncode==0
    except subprocess.TimeoutExpired:return False
def pointer(doc:Any,value:str):
    cur=doc
    for raw in value.split('/')[1:]:
        part=raw.replace('~1','/').replace('~0','~')
        if isinstance(cur,dict) and part in cur:cur=cur[part]
        elif isinstance(cur,list) and part.isdigit() and int(part)<len(cur):cur=cur[int(part)]
        else:raise KeyError(value)
    return cur
def compare(actual:Any,op:str,expected:Any)->bool:
    same=(type(actual) is type(expected) or isinstance(actual,(int,float)) and not isinstance(actual,bool) and isinstance(expected,(int,float)) and not isinstance(expected,bool))
    if op=='eq':return same and actual==expected
    if op=='neq':return not same or actual!=expected
    if op=='contains':return isinstance(actual,(str,list,dict)) and expected in actual
    if op in {'gte','lte'} and isinstance(actual,(int,float)) and not isinstance(actual,bool) and isinstance(expected,(int,float)) and not isinstance(expected,bool):return actual>=expected if op=='gte' else actual<=expected
    return False
def validate(d:Any,root:Path)->tuple[list[str],list[str]]:
    e=[];g=[];keys={'schema_version','receipt_kind','contract','trajectory','artifact_root','artifacts','acceptance','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=keys:e.append(f'root keys must be exactly {sorted(keys)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_completion'}:e.append('receipt_kind invalid')
    contract_ref=d.get('contract',{});trajectory_ref=d.get('trajectory',{});rkeys={'path','sha256'}
    if not isinstance(contract_ref,dict):contract_ref={};e.append('contract binding must be an object')
    if not isinstance(trajectory_ref,dict):trajectory_ref={};e.append('trajectory binding must be an object')
    if set(contract_ref)!=rkeys or set(trajectory_ref)!=rkeys:e.append('contract or trajectory binding shape invalid')
    contract,cp=load_bound(root,contract_ref.get('path'),contract_ref.get('sha256'),'contract',e,g)
    trajectory,tp=load_bound(root,trajectory_ref.get('path'),trajectory_ref.get('sha256'),'trajectory',e,g)
    if cp and not canonical(Path(__file__).with_name('validate-agentic-contract.py'),[str(cp)]):g.append('bound execution contract fails canonical validation')
    if cp and tp and not canonical(Path(__file__).with_name('validate-agentic-trajectory.py'),[str(tp),'--contract',str(cp)]):g.append('bound trajectory fails canonical validation')
    stop=trajectory.get('events',[])[-1] if isinstance(trajectory,dict) and trajectory.get('events') else {}
    if stop.get('phase')!='stop' or stop.get('reason')!='success':g.append('completion requires a successful final trajectory stop')
    try:aroot=confined(root,d.get('artifact_root'))
    except ValueError as ex:g.append(f'artifact root invalid: {ex}');aroot=None
    artifacts=d.get('artifacts',[]);amap={}
    if not isinstance(artifacts,list) or not artifacts:e.append('artifacts required');artifacts=[]
    for i,item in enumerate(artifacts):
        if not isinstance(item,dict) or set(item)!=rkeys or not text(item.get('path')) or not HEX(item.get('sha256')) or item.get('path') in amap:e.append(f'artifact {i} invalid');continue
        if not aroot:continue
        try:path=confined(aroot,item['path']);raw=path.read_bytes();obj=json.loads(raw)
        except (ValueError,OSError,json.JSONDecodeError) as ex:g.append(f'artifact {item.get("path")} unavailable: {ex}');continue
        if sha(raw)!=item['sha256']:g.append(f'artifact {item["path"]} digest mismatch')
        amap[item['path']]=obj
    required_artifacts={o['artifact'] for a in contract.get('acceptance',[]) for o in a.get('oracles',[])} if isinstance(contract,dict) else set()
    if set(amap)!=required_artifacts:g.append('artifact set differs from contract oracle set')
    for path,obj in amap.items():
        vkeys={'schema_version','capture_kind','contract_sha256','trajectory_sha256','revision_before_sha256','revision_after_sha256','scope_diff_sha256','captured_at','runner','commands','acceptance'}
        if not isinstance(obj,dict) or set(obj)!=vkeys or obj.get('schema_version')!=1 or obj.get('capture_kind') not in {'illustrative_fixture','captured_run'} or obj.get('contract_sha256')!=contract_ref.get('sha256') or obj.get('trajectory_sha256')!=trajectory_ref.get('sha256') or any(not HEX(obj.get(k)) for k in ('revision_before_sha256','revision_after_sha256','scope_diff_sha256')) or not ts(obj.get('captured_at')) or not text(obj.get('runner')):g.append(f'artifact {path} provenance invalid')
    required_commands={cmd for step in contract.get('plan',[]) for cmd in step.get('verify',[])} if isinstance(contract,dict) else set();observed_commands={}
    for obj in amap.values():
        commands=obj.get('commands',[]) if isinstance(obj,dict) else []
        if not isinstance(commands,list):continue
        for i,c in enumerate(commands):
            ckeys={'command','exit_code','started_at','completed_at','stdout_sha256','stderr_sha256','timed_out'};start,end=ts(c.get('started_at')) if isinstance(c,dict) else None,ts(c.get('completed_at')) if isinstance(c,dict) else None
            if not isinstance(c,dict) or set(c)!=ckeys or not text(c.get('command')) or c.get('command') in observed_commands or c.get('exit_code')!=0 or not start or not end or end<start or not HEX(c.get('stdout_sha256')) or not HEX(c.get('stderr_sha256')) or c.get('timed_out') is not False:g.append(f'captured verification command {i} invalid')
            else:observed_commands[c['command']]=c
    if set(observed_commands)!=required_commands:g.append('captured verification commands differ from contract plan')
    rows=d.get('acceptance',[]);acceptance={x.get('id'):x for x in rows if isinstance(x,dict)} if isinstance(rows,list) else {}
    if not isinstance(rows,list) or len(acceptance)!=len(rows):e.append('completion acceptance rows must be unique objects')
    expected={x.get('id'):x for x in contract.get('acceptance',[]) if isinstance(x,dict)} if isinstance(contract,dict) else {}
    if set(acceptance)!=set(expected):g.append('completion acceptance set differs from contract')
    for aid,item in expected.items():
        row=acceptance.get(aid,{});rkeys2={'id','requirement_ids','criterion_sha256','oracle_count','oracle_passed'}
        passed=True
        for oracle in item.get('oracles',[]):
            try:actual=pointer(amap[oracle['artifact']],oracle['pointer']);passed=passed and compare(actual,oracle['operator'],oracle['expected'])
            except (KeyError,TypeError):passed=False
        if set(row)!=rkeys2 or row.get('requirement_ids')!=item.get('requirement_ids') or row.get('criterion_sha256')!=sha(item.get('criterion','').encode()) or row.get('oracle_count')!=len(item.get('oracles',[])) or row.get('oracle_passed') is not True or not passed:g.append(f'acceptance {aid} oracle proof invalid')
    for obj in amap.values():
        if isinstance(obj,dict) and set(obj.get('acceptance',{}))!=set(expected):g.append('evidence acceptance result set differs from contract')
    review=d.get('review',{});review=review if isinstance(review,dict) else {};ra,rb=ts(review.get('reviewed_at')),ts(review.get('review_after'))
    rvkeys={'maker','checker','reviewed_at','review_after','approved','scope_diff_reviewed','oracle_sufficiency_reviewed','rollback'}
    if set(review)!=rvkeys or not all(text(review.get(k)) for k in ('maker','checker','rollback')) or review.get('maker')==review.get('checker') or not ra or not rb or rb<=ra or any(review.get(k) is not True for k in ('scope_diff_reviewed','oracle_sufficiency_reviewed')) or not isinstance(review.get('approved'),bool):g.append('independent completion review invalid')
    dec=d.get('decision',{});dec=dec if isinstance(dec,dict) else {}
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'complete','incomplete','reject'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or any(not text(x) for x in dec.get('reasons',[])) or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    captured=all(isinstance(x,dict) and x.get('capture_kind')=='captured_run' for x in amap.values()) and bool(amap)
    if dec.get('outcome')=='complete' and (kind!='captured_completion' or not captured or review.get('approved') is not True or dec.get('unresolved_risks') or e or g):g.append('complete requires captured evidence, independent approval, and no unresolved failure')
    return e,g
def main()->int:
    p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('--evidence-root',default='.');p.add_argument('--json',action='store_true');a=p.parse_args()
    path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d,Path(a.evidence_root));ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('Agentic completion valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
