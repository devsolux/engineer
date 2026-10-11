#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-browser-lane-run.py"
SAMPLE="$ROOT/templates/agentic/browser-session.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$ROOT/templates/agentic/browser-lane-run.sample.json" >/dev/null

make_session() {
  local lane="$1" worker="$2" namespace="$3" mode="$4" account="$5" tenant="$6" start="$7" end="$8"
  mkdir -p "$TMP/$lane-evidence"
  cp "$ROOT/templates/agentic/browser-session-evidence/summary.json" "$TMP/$lane-evidence/summary.json"
  python3 - "$SAMPLE" "$TMP/$lane.json" "$lane" "$worker" "$namespace" "$mode" "$account" "$tenant" "$start" "$end" <<'PY'
import hashlib,json,sys
source,out,lane,worker,namespace,mode,account,tenant,start,end=sys.argv[1:]
d=json.load(open(source)); s=d['session']
s.update(lane=lane,worker_id=worker,namespace=namespace,context_id=f'context-{worker}',started_at=start,ended_at=end)
d['receipt_kind']='captured_session'; d['review'].update(reviewer=f'{worker}-reviewer',approved=True)
d['decision']={'outcome':'pass','reasons':['Captured lane matched policy.'],'unresolved_risks':[]}
d['artifacts'][0]['path']=f'{lane}-evidence/summary.json'
artifact_path=out.rsplit('/',1)[0]+f'/{lane}-evidence/summary.json'
d['artifacts'][0]['sha256']=hashlib.sha256(open(artifact_path,'rb').read()).hexdigest()
if mode!='public_read':
    s.update(risk_class='fixture_write',role='user',auth_mode='synthetic',account_id_sha256=account,tenant_id_sha256=tenant)
    s['storage_state']={'used':True,'source':f'{lane}.json','retained':False,'committed':False,'shared_between_workers':False}
    d['policy']['actions']['allowed'].append('click_submit')
    d['policy']['actions']['mutations']=[{'id':f'approve-{lane}','kind':'click_submit','target':f'fixture:{namespace}','approved':True}]
    d['observations']['actions'][0].update(id=f'action-{lane}',kind='click_submit',target=f'fixture:{namespace}',mutation=True,approval_id=f'approve-{lane}',source='test_spec')
json.dump(d,open(out,'w'),indent=2)
PY
}

A="$(printf account-a | shasum -a 256 | cut -d' ' -f1)"
B="$(printf account-b | shasum -a 256 | cut -d' ' -f1)"
TA="$(printf tenant-a | shasum -a 256 | cut -d' ' -f1)"
TB="$(printf tenant-b | shasum -a 256 | cut -d' ' -f1)"
make_session public worker-0 public-ns public_read null null 2026-07-15T05:00:00Z 2026-07-15T05:03:00Z
make_session write-a worker-1 write-ns-a isolated_write "$A" "$TA" 2026-07-15T05:00:00Z 2026-07-15T05:01:00Z
make_session write-b worker-2 write-ns-b isolated_write "$B" "$TB" 2026-07-15T05:00:00Z 2026-07-15T05:01:00Z

python3 - "$TMP" "$A" "$B" "$TA" "$TB" <<'PY'
import hashlib,json,sys
root,A,B,TA,TB=sys.argv[1:]
h=lambda p:hashlib.sha256(open(root+'/'+p,'rb').read()).hexdigest()
lanes=[]
for lane,mode,worker,namespace,account,tenant in [
 ('public','public_read','worker-0','public-ns',None,None),
 ('write-a','isolated_write','worker-1','write-ns-a',A,TA),
 ('write-b','isolated_write','worker-2','write-ns-b',B,TB),
]:
 lanes.append({'id':lane,'mode':mode,'worker_id':worker,'namespace':namespace,'account_id_sha256':account,'tenant_id_sha256':tenant,'mutation_scope':'read_only' if mode=='public_read' else 'fixture_owned','artifact_root':f'{lane}-evidence','receipt_path':f'{lane}.json','receipt_sha256':h(f'{lane}.json')})
d={'schema_version':1,'run_kind':'captured_run','run_id':'captured-multilane-001','concurrency':{'max_parallel':3,'shared_write_max_parallel':1,'cross_lane_account_overlap':'deny_when_any_lane_writes','artifact_roots_unique':True,'cleanup_required':True},'lanes':lanes,'review':{'reviewer':'aggregate-reviewer','all_sessions_reviewed':True,'isolation_reviewed':True,'cleanup_reviewed':True,'approved':True,'notes':'All captured sessions and ownership boundaries reviewed.'},'decision':{'outcome':'pass','reasons':['All lane and aggregate gates passed.'],'unresolved_risks':[]}}
json.dump(d,open(root+'/run.json','w'),indent=2)
PY
python3 "$VALIDATOR" "$TMP/run.json" >/dev/null
ln -s "$TMP/run.json" "$TMP/run-link.json"
if python3 "$VALIDATOR" "$TMP/run-link.json" >/dev/null 2>&1; then
  echo "expected symlinked browser lane receipt rejection" >&2
  exit 1
fi

mutate() {
  local name="$1" expression="$2"
  python3 - "$TMP/run.json" "$TMP/$name.json" "$expression" <<'PY'
import hashlib,json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d,'hashlib':hashlib,'json':json,'root':sys.argv[1].rsplit('/',1)[0]}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected browser lane run rejection: $name" >&2; exit 1
  fi
}
mutate duplicate_worker 'd["lanes"][2]["worker_id"]=d["lanes"][1]["worker_id"]'
mutate duplicate_namespace 'd["lanes"][2]["namespace"]=d["lanes"][1]["namespace"]'
mutate reused_write_account 'd["lanes"][2]["account_id_sha256"]=d["lanes"][1]["account_id_sha256"]'
mutate reused_write_tenant 'd["lanes"][2]["tenant_id_sha256"]=d["lanes"][1]["tenant_id_sha256"]'
mutate shared_receipt 'd["lanes"][2].update(receipt_path=d["lanes"][1]["receipt_path"],receipt_sha256=d["lanes"][1]["receipt_sha256"])'
mutate shared_artifact_root 'd["lanes"][2]["artifact_root"]=d["lanes"][1]["artifact_root"]'
mutate wrong_scope 'd["lanes"][1]["mutation_scope"]="read_only"'
mutate aggregate_identity_drift 'd["lanes"][1]["account_id_sha256"]="0"*64'
mutate excess_parallelism 'd["concurrency"]["max_parallel"]=2'
mutate self_review 'd["review"]["reviewer"]="worker-1-reviewer"'
mutate illustrative_pass 'd["run_kind"]="illustrative_fixture"'
mutate unresolved_pass 'd["decision"]["unresolved_risks"]=["cleanup unknown"]'
mutate unsafe_receipt_path 'd["lanes"][0]["receipt_path"]="../../outside.json"'
echo "browser lane run fixtures passed"
