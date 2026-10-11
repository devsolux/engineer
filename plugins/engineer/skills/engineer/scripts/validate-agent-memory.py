#!/usr/bin/env python3
'''Validate durable agent-memory admission, retrieval, and lifecycle receipts.'''

from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX=re.compile(r'^[0-9a-f]{64}$')
TYPES={'fact','preference','decision','checkpoint','episode','summary','inference'}
SCOPES={'session','task','project','user','organization','global'}
SOURCES={'trusted_user','system_of_record','tool_output','retrieved_content','peer_agent','agent_inference','summary_model'}
UNTRUSTED={'tool_output','retrieved_content','peer_agent','agent_inference','summary_model'}
STATUSES={'active','quarantine','rejected','expired','tombstone'}
def text(v:Any)->bool:return isinstance(v,str) and bool(v.strip())
def ts(v:Any):
    try:return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) else None
    except ValueError:return None

def validate(d:Any)->tuple[list[str],list[str]]:
    e=[];g=[]
    keys={'schema_version','receipt_kind','store','policy','entries','retrievals','lifecycle','tests','review','decision'}
    if not isinstance(d,dict):return ['root must be an object'],[]
    if set(d)!=keys:e.append(f'root keys must be exactly {sorted(keys)}')
    if d.get('schema_version')!=1:e.append('schema_version must be 1')
    kind=d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_review'}:e.append('invalid receipt_kind')
    store=d.get('store',{});skeys={'name','environment','owner','tenant_field','subject_field','rls_or_authz','encrypted_at_rest','replicas','derived_stores'}
    if set(store)!=skeys or not all(text(store.get(k)) for k in ('name','environment','owner','tenant_field','subject_field','rls_or_authz')) or store.get('encrypted_at_rest') is not True or not isinstance(store.get('replicas'),list) or not isinstance(store.get('derived_stores'),list):g.append('memory store identity, isolation, encryption, or replica inventory incomplete')
    p=d.get('policy',{});pkeys={'allowed_types','allowed_scopes','max_retention_days','default_retention_days','max_retrieval_items','max_retrieval_tokens','raw_secrets_forbidden','memory_grants_authority','access_before_ranking','provenance_returned','contradictions_returned','deletion_covers_derived','export_supported','rectification_supported'}
    if set(p)!=pkeys or set(p.get('allowed_types',[]))!=TYPES or set(p.get('allowed_scopes',[]))!=SCOPES or not isinstance(p.get('max_retention_days'),int) or p.get('max_retention_days',0)<1 or not isinstance(p.get('default_retention_days'),int) or not 1<=p.get('default_retention_days',0)<=p.get('max_retention_days',0) or not isinstance(p.get('max_retrieval_items'),int) or p.get('max_retrieval_items',0)<1 or not isinstance(p.get('max_retrieval_tokens'),int) or p.get('max_retrieval_tokens',0)<1 or p.get('raw_secrets_forbidden') is not True or p.get('memory_grants_authority') is not False or any(p.get(k) is not True for k in ('access_before_ranking','provenance_returned','contradictions_returned','deletion_covers_derived','export_supported','rectification_supported')):g.append('memory policy incomplete')

    entries=d.get('entries',[]);emap={};active_by_key={}
    ekeys={'id','key','type','scope','tenant_id','subject_id','purpose','source','content_sha256','sensitivity','consent','created_at','expires_at','authority','verification','supersedes','contradicts','status','rollback'}
    if not isinstance(entries,list) or not entries:e.append('entries required');entries=[]
    for i,x in enumerate(entries):
        if not isinstance(x,dict) or set(x)!=ekeys:e.append(f'entry {i} keys invalid');continue
        eid=x.get('id')
        if not text(eid) or eid in emap or not text(x.get('key')) or x.get('type') not in TYPES or x.get('scope') not in SCOPES or not text(x.get('tenant_id')) or not text(x.get('subject_id')) or not text(x.get('purpose')) or x.get('sensitivity') not in {'public','internal','pii','secret'} or x.get('status') not in STATUSES or not HEX.fullmatch(str(x.get('content_sha256',''))) or x.get('authority') is not False or not text(x.get('rollback')):e.append(f'entry {i} identity invalid');continue
        emap[eid]=x
        source=x.get('source',{})
        if set(source)!={'type','locator','captured_at','trust'} or source.get('type') not in SOURCES or not text(source.get('locator')) or not ts(source.get('captured_at')) or source.get('trust') not in {'untrusted','user_asserted','verified'}:e.append(f'entry {eid} source invalid')
        created,expires=ts(x.get('created_at')),ts(x.get('expires_at'))
        if not created or not expires or expires<=created or (expires-created).days>p.get('max_retention_days',0):g.append(f'entry {eid} expiry invalid')
        consent=x.get('consent',{})
        if set(consent)!={'required','obtained','basis','at'} or not isinstance(consent.get('required'),bool) or not isinstance(consent.get('obtained'),bool) or not text(consent.get('basis')) or (consent.get('required') and (consent.get('obtained') is not True or not ts(consent.get('at')))):g.append(f'entry {eid} consent invalid')
        verification=x.get('verification',{})
        if set(verification)!={'required','evidence','reviewer','independent'} or not isinstance(verification.get('required'),bool) or not isinstance(verification.get('evidence'),list) or any(not text(v) for v in verification.get('evidence',[])) or not text(verification.get('reviewer')) or not isinstance(verification.get('independent'),bool):e.append(f'entry {eid} verification invalid')
        if x.get('sensitivity')=='secret':g.append(f'entry {eid} stores forbidden secret material')
        if x.get('sensitivity')=='pii' and (consent.get('required') is not True or consent.get('obtained') is not True):g.append(f'entry {eid} PII lacks consent/lawful basis gate')
        if source.get('type') in UNTRUSTED and x.get('status')=='active' and (verification.get('required') is not True or not verification.get('evidence') or verification.get('independent') is not True or source.get('trust')!='verified'):g.append(f'entry {eid} activates untrusted or derived memory without independent verification')
        if source.get('type')=='system_of_record' and x.get('status')=='active' and source.get('trust')!='verified':g.append(f'entry {eid} system fact is not verified')
        if source.get('type')=='trusted_user' and x.get('type')=='preference' and x.get('status')=='active' and source.get('trust')!='user_asserted':g.append(f'entry {eid} preference lacks user assertion')
        if x.get('scope')=='global' and (source.get('type')!='system_of_record' or source.get('trust')!='verified' or x.get('sensitivity') not in {'public','internal'}):g.append(f'entry {eid} unsafe global scope')
        if not isinstance(x.get('supersedes'),list) or not isinstance(x.get('contradicts'),list):e.append(f'entry {eid} lifecycle refs invalid')
        if x.get('status')=='active':active_by_key.setdefault((x.get('tenant_id'),x.get('subject_id'),x.get('key')),[]).append(eid)
    for eid,x in emap.items():
        refs=set(x.get('supersedes',[]))|set(x.get('contradicts',[]))
        if not refs.issubset(set(emap)) or eid in refs:g.append(f'entry {eid} has invalid lifecycle references')
    for key,ids in active_by_key.items():
        if len(ids)>1:g.append(f'multiple active memories for semantic key: {key}')

    reads=d.get('retrievals',[]);rkeys={'id','purpose','tenant_id','subject_id','scope','query_sha256','entry_ids','item_limit','token_limit','access_checked','ranking_after_access','provenance_included','trust_included','freshness_included','contradictions_included','used_as_authority','citations'}
    if not isinstance(reads,list) or not reads:e.append('retrievals required');reads=[]
    retrieval_ids=set()
    for i,r in enumerate(reads):
        if not isinstance(r,dict) or set(r)!=rkeys:e.append(f'retrieval {i} keys invalid');continue
        ids=r.get('entry_ids',[])
        rid=r.get('id')
        if not text(rid) or rid in retrieval_ids or not text(r.get('purpose')) or not text(r.get('tenant_id')) or not text(r.get('subject_id')) or r.get('scope') not in SCOPES or not HEX.fullmatch(str(r.get('query_sha256',''))) or not isinstance(ids,list) or len(ids)!=len(set(ids)) or not isinstance(r.get('item_limit'),int) or not 1<=r.get('item_limit',0)<=p.get('max_retrieval_items',0) or len(ids)>r.get('item_limit',0) or not isinstance(r.get('token_limit'),int) or not 1<=r.get('token_limit',0)<=p.get('max_retrieval_tokens',0):e.append(f'retrieval {i} identity or budget invalid');continue
        retrieval_ids.add(rid)
        if any(v not in emap for v in ids):e.append(f'retrieval {i} references unknown entry')
        for eid in ids:
            x=emap.get(eid,{})
            if x.get('status')!='active' or x.get('tenant_id')!=r.get('tenant_id') or x.get('subject_id')!=r.get('subject_id') or x.get('purpose')!=r.get('purpose') or x.get('scope')!=r.get('scope'):g.append(f'retrieval {i} used ineligible memory {eid}')
        citations=r.get('citations',[])
        if any(r.get(k) is not True for k in ('access_checked','ranking_after_access','provenance_included','trust_included','freshness_included','contradictions_included')) or r.get('used_as_authority') is not False or not isinstance(citations,list) or any(not text(v) for v in citations) or len(citations)<len(ids):g.append(f'retrieval {i} context controls incomplete')

    life=d.get('lifecycle',[]);lkeys={'operation','entry_id','actor','at','authorized','content_removed','embeddings_removed','caches_removed','replicas_addressed','audit_event'}
    if not isinstance(life,list) or not life:e.append('lifecycle operations required');life=[]
    lifecycle_seen=set()
    status_for={'admit':'active','quarantine':'quarantine','reject':'rejected','rectify':'active','expire':'expired','delete':'tombstone'}
    for i,x in enumerate(life):
        if not isinstance(x,dict) or set(x)!=lkeys or x.get('operation') not in {'admit','quarantine','reject','rectify','expire','delete','export'} or x.get('entry_id') not in emap or not text(x.get('actor')) or not ts(x.get('at')) or x.get('authorized') is not True or not text(x.get('audit_event')):e.append(f'lifecycle {i} invalid');continue
        lifecycle_seen.add(x.get('entry_id'))
        expected=status_for.get(x.get('operation'))
        if expected and emap[x.get('entry_id')].get('status')!=expected:g.append(f'lifecycle {i} operation does not match entry status')
        if x.get('operation')=='rectify' and not emap[x.get('entry_id')].get('supersedes'):g.append(f'lifecycle {i} rectification lacks superseded entry')
        if x.get('operation') in {'expire','delete'} and any(x.get(k) is not True for k in ('content_removed','embeddings_removed','caches_removed','replicas_addressed')):g.append(f'lifecycle {i} incomplete derived-state removal')
    if set(emap)-lifecycle_seen:g.append('every declared entry requires a lifecycle receipt')
    tests=d.get('tests',{})
    if set(tests)!={'benign_preference','untrusted_injection','cross_tenant','contradiction','expiry','deletion_resurrection','passed'} or any(tests.get(k) is not True for k in tests):g.append('memory regression coverage incomplete')
    review=d.get('review',{})
    reviewed_at,review_after=ts(review.get('reviewed_at')),ts(review.get('review_after'))
    if set(review)!={'owner','independent_reviewer','reviewed_at','review_after','approved','rollback'} or not all(text(review.get(k)) for k in ('owner','independent_reviewer','rollback')) or not reviewed_at or not review_after or review_after<=reviewed_at or review.get('owner')==review.get('independent_reviewer') or not isinstance(review.get('approved'),bool):g.append('independent memory review invalid')
    dec=d.get('decision',{})
    if set(dec)!={'outcome','reasons','unresolved_risks'} or dec.get('outcome') not in {'admit','quarantine','reject'} or not isinstance(dec.get('reasons'),list) or not dec.get('reasons') or not isinstance(dec.get('unresolved_risks'),list):e.append('decision invalid')
    if dec.get('outcome')=='admit' and (kind!='captured_review' or review.get('approved') is not True or dec.get('unresolved_risks')):g.append('admission requires captured approved review with no unresolved risks')
    return e,g

def main()->int:
    p=argparse.ArgumentParser();p.add_argument('receipt');p.add_argument('--json',action='store_true');a=p.parse_args()
    path=regular_input_file(a.receipt)
    if path is None:print('receipt must be a regular file, not a symlink',file=sys.stderr);return 2
    try:d=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError) as ex:print(ex,file=sys.stderr);return 2
    e,g=validate(d);ok=not e and not g;out={'valid':ok,'errors':e,'gates':g}
    print(json.dumps(out,indent=2) if a.json else ('agent memory receipt valid' if ok else '\n'.join([*(f'error: {x}' for x in e),*(f'gate: {x}' for x in g)])))
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
