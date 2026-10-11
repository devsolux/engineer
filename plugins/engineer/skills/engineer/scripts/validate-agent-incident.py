#!/usr/bin/env python3
'''Validate an evidence-bound agent incident response receipt.'''

from __future__ import annotations

import argparse, hashlib, json, re, sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX64 = re.compile(r'^[0-9a-f]{64}$')
SEVERITIES = {'low', 'medium', 'high', 'critical'}
STATUSES = {'declared', 'contained', 'recovering', 'closed'}
BLAST = {'credentials', 'repositories', 'data', 'production', 'money', 'external_side_effects', 'downstream_agents'}
PERSISTENCE = {'skills_instructions', 'hooks_startup', 'mcp_tools', 'schedules_ci', 'browser_profiles', 'rag_memory_cache', 'checkpoints', 'cloud_tasks', 'delegated_agents'}
CONTAIN = {'freeze_automation', 'isolate', 'disable_capabilities', 'revoke_credentials'}

def txt(v: Any) -> bool: return isinstance(v, str) and bool(v.strip())
def when(v: Any) -> datetime | None:
    try: return datetime.fromisoformat(v.replace('Z', '+00:00')) if isinstance(v, str) else None
    except ValueError: return None
def rel(v: Any) -> PurePosixPath | None:
    if not txt(v): return None
    p = PurePosixPath(v)
    return None if p.is_absolute() or '..' in p.parts or '.' in p.parts else p
def digest(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()

def validate(d: Any, root: Path) -> tuple[list[str], list[str]]:
    e: list[str] = []; g: list[str] = []
    keys = {'schema_version','receipt_kind','incident','roles','evidence','containment','blast_radius','persistence_audit','eradication','recovery','notifications','regression','decision'}
    if not isinstance(d, dict): return ['root must be an object'], []
    if set(d) != keys: e.append(f'root keys must be exactly {sorted(keys)}')
    if d.get('schema_version') != 1: e.append('schema_version must be 1')
    kind = d.get('receipt_kind')
    if kind not in {'illustrative_fixture','captured_incident'}: e.append('invalid receipt_kind')
    inc = d.get('incident', {})
    if set(inc) != {'id','severity','status','detected_at','declared_at','summary','affected_systems','uncertainties'}: e.append('incident keys invalid')
    if not txt(inc.get('id')) or inc.get('severity') not in SEVERITIES or inc.get('status') not in STATUSES: e.append('incident identity, severity, or status invalid')
    detected, declared = when(inc.get('detected_at')), when(inc.get('declared_at'))
    if not detected or not declared or declared < detected: e.append('incident timestamps invalid or out of order')
    for k in ('summary',):
        if not txt(inc.get(k)): e.append(f'incident.{k} required')
    for k in ('affected_systems','uncertainties'):
        if not isinstance(inc.get(k), list) or any(not txt(x) for x in inc.get(k, [])): e.append(f'incident.{k} must be a text array')
    roles = d.get('roles', {})
    if set(roles) != {'incident_commander','evidence_reviewer'} or not all(txt(roles.get(k)) for k in roles): e.append('roles invalid')
    elif roles['incident_commander'] == roles['evidence_reviewer']: g.append('incident commander cannot independently review evidence')

    evidence = d.get('evidence', {})
    if set(evidence) != {'artifacts','custody'}: e.append('evidence keys invalid')
    arts = evidence.get('artifacts', []) if isinstance(evidence, dict) else []
    kinds = set()
    if not isinstance(arts, list) or not arts: e.append('evidence.artifacts required'); arts=[]
    for i,a in enumerate(arts):
        if not isinstance(a,dict) or set(a) != {'id','kind','path','sha256','captured_at','captured_by','volatile','contains_secrets'}: e.append(f'artifact {i} keys invalid'); continue
        p = rel(a.get('path')); kinds.add(a.get('kind'))
        if not txt(a.get('id')) or a.get('kind') not in {'trace','log','config','state','image','network'} or not p or not HEX64.fullmatch(str(a.get('sha256',''))) or not when(a.get('captured_at')) or not txt(a.get('captured_by')): e.append(f'artifact {i} metadata invalid'); continue
        fp = root / p
        if not fp.is_file() or digest(fp) != a['sha256']: e.append(f'artifact {i} missing or hash mismatch')
        if a.get('contains_secrets') is not False: g.append(f'artifact {i} may expose raw secrets')
    if not {'trace','config','state'}.issubset(kinds): g.append('trace, config, and state evidence are required')
    custody = evidence.get('custody', []) if isinstance(evidence,dict) else []
    last = None
    if not isinstance(custody,list) or not custody: e.append('chain of custody required'); custody=[]
    ids = {a.get('id') for a in arts if isinstance(a,dict)}
    for i,c in enumerate(custody):
        if not isinstance(c,dict) or set(c) != {'artifact_id','at','actor','action','sha256'}: e.append(f'custody {i} keys invalid'); continue
        t=when(c.get('at'))
        if c.get('artifact_id') not in ids or not t or not txt(c.get('actor')) or not txt(c.get('action')) or not HEX64.fullmatch(str(c.get('sha256',''))): e.append(f'custody {i} invalid')
        if last and t and t < last: e.append('custody timestamps must be monotonic')
        if t: last=t

    actions=d.get('containment',[])
    seen=set()
    if not isinstance(actions,list): e.append('containment must be an array'); actions=[]
    for i,a in enumerate(actions):
        if not isinstance(a,dict) or set(a) != {'action','status','completed_at','evidence_ids','notes'}: e.append(f'containment {i} keys invalid'); continue
        seen.add(a.get('action'))
        if a.get('action') not in CONTAIN | {'deny_egress'} or a.get('status') not in {'complete','not_applicable'} or not when(a.get('completed_at')) or not isinstance(a.get('evidence_ids'),list) or any(x not in ids for x in a.get('evidence_ids',[])) or not txt(a.get('notes')): e.append(f'containment {i} invalid')
        if a.get('status') == 'complete' and not a.get('evidence_ids'): g.append(f'containment {a.get("action")} lacks evidence')
    if not CONTAIN.issubset(seen): g.append('mandatory containment actions not assessed')
    if inc.get('severity') == 'critical' and 'deny_egress' not in seen: g.append('critical incident must assess denied egress')

    def assessment(name: str, required: set[str]) -> None:
        rows=d.get(name,[])
        if not isinstance(rows,list): e.append(f'{name} must be an array'); return
        got=set()
        for i,x in enumerate(rows):
            if not isinstance(x,dict) or set(x) != {'surface','result','evidence_ids','notes'}: e.append(f'{name} {i} keys invalid'); continue
            got.add(x.get('surface'))
            if x.get('surface') not in required or x.get('result') not in {'affected','clear','unknown'} or not isinstance(x.get('evidence_ids'),list) or any(v not in ids for v in x.get('evidence_ids',[])) or not txt(x.get('notes')): e.append(f'{name} {i} invalid')
            if x.get('result') == 'unknown': g.append(f'{name} unresolved: {x.get("surface")}')
        if got != required: g.append(f'{name} must assess exactly {sorted(required)}')
    assessment('blast_radius',BLAST); assessment('persistence_audit',PERSISTENCE)

    era=d.get('eradication',{})
    if set(era) != {'evidence_preserved_before_cleanup','malicious_state_removed','root_boundary_fixed','credentials_revoked_before_rotation','poisoned_state_invalidated','known_good_source_sha256','actions'}: e.append('eradication keys invalid')
    for k in ('evidence_preserved_before_cleanup','malicious_state_removed','root_boundary_fixed','credentials_revoked_before_rotation','poisoned_state_invalidated'):
        if era.get(k) is not True: g.append(f'eradication.{k} is not proven')
    if not HEX64.fullmatch(str(era.get('known_good_source_sha256',''))): g.append('known-good immutable source digest required')
    if not isinstance(era.get('actions'),list) or not era.get('actions') or any(not txt(x) for x in era.get('actions',[])): e.append('eradication.actions required')
    if any(re.search(r'(token|password|secret)\s*[:=]\s*\S+', x, re.I) for x in era.get('actions',[]) if isinstance(x,str)): g.append('eradication actions may contain raw credentials')

    rec=d.get('recovery',{})
    if set(rec) != {'mode','reused_contaminated_state','monitoring','exit_criteria','new_indicators','evidence_ids'}: e.append('recovery keys invalid')
    if rec.get('mode') not in {'read_only','canary','full'} or rec.get('reused_contaminated_state') is not False: g.append('recovery must reject contaminated state and use a valid stage')
    for k in ('monitoring','exit_criteria'):
        if not isinstance(rec.get(k),list) or not rec.get(k) or any(not txt(x) for x in rec.get(k,[])): g.append(f'recovery.{k} required')
    if not isinstance(rec.get('new_indicators'),list): e.append('recovery.new_indicators must be an array')
    elif rec['new_indicators']: g.append('new indicators require recontainment')
    if not isinstance(rec.get('evidence_ids'),list) or any(x not in ids for x in rec.get('evidence_ids',[])): e.append('recovery evidence invalid')

    notif=d.get('notifications',[])
    if not isinstance(notif,list) or not notif: g.append('notification decisions required')
    else:
        for i,n in enumerate(notif):
            if not isinstance(n,dict) or set(n) != {'audience','decision','rationale'} or n.get('decision') not in {'notify','not_required','pending'} or not txt(n.get('audience')) or not txt(n.get('rationale')): e.append(f'notification {i} invalid')
            elif n['decision']=='pending': g.append(f'notification pending: {n["audience"]}')
    reg=d.get('regression',{})
    if set(reg) != {'incident_case','benign_control','root_fix_test','passed','evidence_ids'} or not all(txt(reg.get(k)) for k in ('incident_case','benign_control','root_fix_test')) or reg.get('passed') is not True: g.append('malicious, benign-control, and root-fix regressions must pass')
    if not isinstance(reg.get('evidence_ids'),list) or any(x not in ids for x in reg.get('evidence_ids',[])): e.append('regression evidence invalid')
    dec=d.get('decision',{})
    if set(dec) != {'outcome','unresolved_risks','closed_at','review_after','rationale'} or dec.get('outcome') not in {'remain_open','close'} or not isinstance(dec.get('unresolved_risks'),list) or any(not txt(x) for x in dec.get('unresolved_risks',[])) or not txt(dec.get('rationale')): e.append('decision invalid')
    if dec.get('outcome') == 'close':
        if kind != 'captured_incident': g.append('only captured_incident may close')
        if inc.get('status') != 'closed' or not when(dec.get('closed_at')) or not when(dec.get('review_after')): g.append('closure timestamps and incident status required')
        if dec.get('unresolved_risks'): g.append('closed incident has unresolved risks')
    elif inc.get('status') == 'closed': g.append('closed status conflicts with remain_open')
    return e,g

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('receipt'); p.add_argument('--json',action='store_true'); a=p.parse_args()
    path=regular_input_file(a.receipt)
    if path is None: print('receipt must be a regular file, not a symlink',file=sys.stderr); return 2
    try: data=json.loads(path.read_text())
    except (OSError,json.JSONDecodeError) as ex: print(ex,file=sys.stderr); return 2
    errors,gates=validate(data,path.parent)
    ok=not errors and not gates
    result={'valid':ok,'errors':errors,'gates':gates}
    print(json.dumps(result,indent=2) if a.json else ('agent incident receipt valid' if ok else '\n'.join([*(f'error: {x}' for x in errors),*(f'gate: {x}' for x in gates)])))
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
