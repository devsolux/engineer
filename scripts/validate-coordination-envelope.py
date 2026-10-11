#!/usr/bin/env python3
'''Validate a transport notification against an orchestration contract and local artifact.'''

from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0,str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX=re.compile(r'^[0-9a-f]{64}$')
IDENT=re.compile(r'^[a-z][a-z0-9_-]{1,63}$')
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else None
    except ValueError:return None
def digest(path:Path)->str:return hashlib.sha256(path.read_bytes()).hexdigest()
def confined(v:Any)->bool:
    if not text(v):return False
    p=PurePosixPath(v)
    return not p.is_absolute() and '..' not in p.parts and '.' not in p.parts
def matches_schema(value:Any,schema:Any)->bool:
    if not isinstance(schema,dict):return False
    kind=schema.get('type')
    checks={'object':lambda v:isinstance(v,dict),'array':lambda v:isinstance(v,list),'string':lambda v:isinstance(v,str),'number':lambda v:isinstance(v,(int,float)) and not isinstance(v,bool),'integer':lambda v:isinstance(v,int) and not isinstance(v,bool),'boolean':lambda v:isinstance(v,bool),'null':lambda v:v is None}
    if kind not in checks or not checks[kind](value):return False
    if kind=='object':
        required=schema.get('required',[])
        if not isinstance(required,list) or any(not text(x) for x in required) or not set(required).issubset(set(value)):return False
        props=schema.get('properties',{})
        if props is not None:
            if not isinstance(props,dict):return False
            for key,child in props.items():
                if key in value and not matches_schema(value[key],child):return False
    if kind=='array' and 'items' in schema and any(not matches_schema(x,schema['items']) for x in value):return False
    return True

def validate(d:Any,root:Path,artifact_root:Path)->tuple[list[str],list[str]]:
    e=[];g=[]
    rkeys={'schema_version','receipt_kind','transport','message','contract','pointer','receiver','ack','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=rkeys:e.append(f'root keys must be exactly {sorted(rkeys)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_delivery'}:e.append('invalid receipt_kind')

    tr=d.get('transport',{});tkeys={'name','channel','delivery_scope','delivery_id','sender_label_authenticated','live_required','max_payload_bytes','retention'}
    if set(tr)!=tkeys or not all(text(tr.get(k)) for k in ('name','channel','delivery_id','retention')) or tr.get('delivery_scope') not in {'exact_session','repository','workspace'} or not isinstance(tr.get('sender_label_authenticated'),bool) or not isinstance(tr.get('live_required'),bool) or not isinstance(tr.get('max_payload_bytes'),int) or not 1<=tr.get('max_payload_bytes',0)<=8192:g.append('transport policy invalid or overbroad')

    m=d.get('message',{});mkeys={'id','sent_at','from','to','content_type','contains_sensitive_data','contains_instructions','grants_authority','payload_bytes','quota_signal'}
    if set(m)!=mkeys or not all(text(m.get(k)) for k in ('id','from','to')) or not ts(m.get('sent_at')) or m.get('content_type')!='artifact_pointer' or not isinstance(m.get('payload_bytes'),int) or not 1<=m.get('payload_bytes',0)<=tr.get('max_payload_bytes',0):e.append('message identity, type, or size invalid')
    if any(m.get(k) is not False for k in ('contains_sensitive_data','contains_instructions','grants_authority')):g.append('message contains forbidden data, instructions, or authority')
    quota=m.get('quota_signal',{});qkeys={'source','observed_at','availability','used_for_scheduling_only'}
    if set(quota)!=qkeys or not text(quota.get('source')) or not ts(quota.get('observed_at')) or quota.get('availability') not in {'ready','limited','blocked','unknown'} or quota.get('used_for_scheduling_only') is not True:g.append('quota signal is invalid or authority-bearing')
    if ts(quota.get('observed_at')) and ts(m.get('sent_at')) and ts(quota.get('observed_at'))>ts(m.get('sent_at')):g.append('quota observation follows message send')

    c=d.get('contract',{});ckeys={'id','path','sha256','task_id','declared_sender','declared_receiver','output_ref'}
    if set(c)!=ckeys or not IDENT.fullmatch(str(c.get('id',''))) or not IDENT.fullmatch(str(c.get('task_id',''))) or not all(text(c.get(k)) for k in ('declared_sender','declared_receiver')) or not confined(c.get('path')) or not confined(c.get('output_ref')) or not HEX.fullmatch(str(c.get('sha256',''))):e.append('contract pointer invalid')
    contract={};contract_path=(root/c.get('path','')).resolve();contract_valid=False;receiver_schema={}
    try:
        if not contract_path.is_relative_to(root.resolve()):raise ValueError('escape')
        if digest(contract_path)!=c.get('sha256'):g.append('orchestration contract digest mismatch')
        contract=json.loads(contract_path.read_text())
        validator=Path(__file__).with_name('validate-orchestration-contract.py')
        result=subprocess.run([sys.executable,str(validator),str(contract_path),'--json'],capture_output=True,text=True,timeout=10,check=False)
        contract_valid=result.returncode==0
        if not contract_valid:g.append('referenced orchestration contract fails its validator')
    except (OSError,ValueError,json.JSONDecodeError):e.append('orchestration contract unavailable or outside root')
    if contract:
        if contract.get('goal',{}).get('id')!=c.get('id'):g.append('contract identity mismatch')
        matches=[x for x in contract.get('delegations',[]) if x.get('task_id')==c.get('task_id')]
        if len(matches)!=1:g.append('task does not resolve to one delegation')
        else:
            x=matches[0]
            if (x.get('from'),x.get('to'),x.get('output_ref'))!=(c.get('declared_sender'),c.get('declared_receiver'),c.get('output_ref')):g.append('sender, receiver, or output does not match delegation')
        receivers=[a for a in contract.get('agents',[]) if a.get('id')==c.get('declared_receiver')]
        if len(receivers)!=1:g.append('declared receiver does not resolve to one contract agent')
        else:receiver_schema=receivers[0].get('output_schema',{})
    if (m.get('from'),m.get('to'))!=(c.get('declared_sender'),c.get('declared_receiver')):g.append('message labels do not match declared delegation')

    p=d.get('pointer',{});pkeys={'artifact_path','sha256','schema','state','expires_at','nonce','sensitivity','executable'}
    expected_schema=f'orchestration-output:{c.get("declared_receiver","")}'
    if set(p)!=pkeys or not confined(p.get('artifact_path')) or not HEX.fullmatch(str(p.get('sha256',''))) or p.get('schema')!=expected_schema or p.get('state') not in {'ready','failed','cancelled'} or not ts(p.get('expires_at')) or not text(p.get('nonce')) or p.get('sensitivity') not in {'public','internal'} or p.get('executable') is not False:e.append('artifact pointer invalid')
    if p.get('artifact_path')!=c.get('output_ref'):g.append('artifact path does not match contract output')
    sent,expires=ts(m.get('sent_at')),ts(p.get('expires_at'))
    if sent and expires and expires<=sent:g.append('pointer expiry does not follow send time')
    artifact_path=(artifact_root/p.get('artifact_path','')).resolve()
    try:
        if not artifact_path.is_relative_to(artifact_root.resolve()):raise ValueError('escape')
        if digest(artifact_path)!=p.get('sha256'):g.append('artifact digest mismatch')
        artifact=json.loads(artifact_path.read_text())
        if not matches_schema(artifact,receiver_schema):g.append('artifact does not satisfy receiver output schema')
    except (OSError,ValueError,json.JSONDecodeError):e.append('artifact unavailable, invalid, or outside root')

    rv=d.get('receiver',{});rvkeys={'id','received_at','contract_loaded','recipient_matched','task_transition_valid','expiry_valid','path_confined','digest_verified','schema_valid','replayed','executed_from_message','persisted_as_memory','outcome'}
    if set(rv)!=rvkeys or rv.get('id')!=c.get('declared_receiver') or not ts(rv.get('received_at')) or rv.get('outcome') not in {'accepted','quarantine','rejected'}:e.append('receiver receipt invalid')
    if any(rv.get(k) is not True for k in ('contract_loaded','recipient_matched','task_transition_valid','expiry_valid','path_confined','digest_verified','schema_valid')) or any(rv.get(k) is not False for k in ('replayed','executed_from_message','persisted_as_memory')):g.append('receiver safety checks incomplete')
    received=ts(rv.get('received_at'))
    if sent and received and received<sent:g.append('receiver timestamp precedes send')
    if received and expires and received>=expires:g.append('receiver accepted an expired pointer')

    ack=d.get('ack',{});akeys={'idempotency_key','status','at','artifact_sha256'}
    if set(ack)!=akeys or not text(ack.get('idempotency_key')) or ack.get('status') not in {'accepted','quarantined','rejected'} or not ts(ack.get('at')) or ack.get('artifact_sha256')!=p.get('sha256'):e.append('acknowledgment invalid')
    expected_ack={'accepted':'accepted','quarantine':'quarantined','rejected':'rejected'}.get(rv.get('outcome'))
    if ack.get('status')!=expected_ack:g.append('acknowledgment conflicts with receiver outcome')
    ack_at=ts(ack.get('at'))
    if received and ack_at and ack_at<received:g.append('acknowledgment precedes receipt')

    review=d.get('review',{});reviewed,after=ts(review.get('reviewed_at')),ts(review.get('review_after'))
    if set(review)!={'owner','independent_reviewer','reviewed_at','review_after','approved','rollback'} or not all(text(review.get(k)) for k in ('owner','independent_reviewer','rollback')) or review.get('owner')==review.get('independent_reviewer') or not reviewed or not after or after<=reviewed or not isinstance(review.get('approved'),bool):g.append('independent review invalid')
    if ack_at and reviewed and reviewed<ack_at:g.append('review precedes acknowledgment')
    dec=d.get('decision',{})
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'accept','quarantine','reject'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or any(not text(x) for x in dec.get('reasons',[])) or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    contract_approved=contract_valid and contract.get('receipt_kind')=='captured_contract' and contract.get('review',{}).get('approved') is True
    if dec.get('outcome')=='accept' and (kind!='captured_delivery' or review.get('approved') is not True or dec.get('unresolved_risks') or rv.get('outcome')!='accepted' or not contract_approved):g.append('accept requires captured approved contract and delivery with no unresolved risk')
    if dec.get('outcome')!='accept' and rv.get('outcome')=='accepted':g.append('receiver acceptance conflicts with decision')
    return e,g

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('receipt');ap.add_argument('--root',default='.');ap.add_argument('--artifact-root');ap.add_argument('--json',action='store_true');a=ap.parse_args()
    path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    root=Path(a.root);artifact_root=Path(a.artifact_root) if a.artifact_root else root
    e,g=validate(d,root,artifact_root);ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('coordination envelope valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
