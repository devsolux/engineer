#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-security-coverage.py"
SAMPLE="$ROOT/templates/agentic/security-coverage.sample.json"
EVIDENCE="templates/agentic/security-audit-evidence"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["valid"] and not d["errors"] and not d["gates"], d'

# Document-only mutations. Unit order in the sample: http-api units 0-5 (covered,
# covered, candidate, covered, candidate, candidate), admin-cli units 6-8
# (not_applicable) and 9-11 (deferred).
write_mutation() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1], encoding="utf-8"))
def recount():
    counts={k:0 for k in d["summary"]["by_status"]}
    for u in d["units"]: counts[u["status"]]+=1
    d["summary"]["by_status"]=counts; d["summary"]["units"]=len(d["units"])
exec(sys.argv[3], {"d":d,"recount":recount}); json.dump(d,open(sys.argv[2],"w",encoding="utf-8"))
PY
}

mutate() {
  local name="$1" expression="$2"
  write_mutation "$name" "$expression"
  if python3 "$VALIDATOR" "$TMP/$name.json" --evidence-root "$ROOT" >/dev/null 2>&1; then
    echo "expected coverage rejection: $name" >&2
    exit 1
  fi
}

accept() {
  local name="$1" expression="$2"
  write_mutation "$name" "$expression"
  if ! python3 "$VALIDATOR" "$TMP/$name.json" --evidence-root "$ROOT" >"$TMP/$name.out" 2>&1; then
    echo "expected coverage acceptance: $name" >&2
    cat "$TMP/$name.out" >&2
    exit 1
  fi
}

accept incomplete_with_planned_and_reason 'u=d["units"][9]; u.update({"status":"planned","unresolved_reason":None}); d["run"]["status"]="incomplete"; d["run"]["incomplete_reason"]="admin-cli export path not yet hunted"; recount()'
accept carried_unchanged_without_wave 'd["run"]["prior_runs"]=["run-000"]; u=d["units"][0]; u.update({"owner":None,"wave":None,"carried_from":{"run_id":"run-000","prior_status":"covered","source_changed":False}})'
accept critic_proposed_unit 'd["units"][0]["proposed_by"]="critic-a"'

mutate wrong_id 'd["units"][0]["coverage_id"]="cov-000000000000"'
mutate duplicate_tuple 'd["units"][1]=dict(d["units"][0])'
mutate unknown_surface 'd["units"][0]["surface"]="mobile"'
mutate class_outside_catalog 'd["dimensions"]["attack_classes"].append("phishing")'
mutate covered_without_paths 'd["units"][0]["reviewed_paths"]=[]'
mutate covered_without_checks 'd["units"][0]["checks"]=[]'
mutate candidate_without_fingerprint 'd["units"][2]["candidate_fingerprints"]=[]'
mutate blocked_without_reason 'd["units"][9].update({"status":"blocked","unresolved_reason":None}); recount()'
mutate planned_with_owner 'd["units"][9].update({"status":"planned","unresolved_reason":None,"owner":"hunter-a"}); d["run"]["status"]="incomplete"; d["run"]["incomplete_reason"]="pending"; recount()'
mutate local_check_without_sandbox 'd["run"]["sandbox"]={"available":False,"unavailable_reason":"no OS sandbox on this host"}; d["units"][0]["checks"][0]["method"]="local"'
mutate critic_also_hunter 'd["waves"][0]["critic"]="hunter-a"'
mutate proposed_by_not_critic 'd["units"][0]["proposed_by"]="hunter-b"'
mutate proposed_by_is_owner 'd["waves"].append({"wave":2,"hunters":["critic-a"],"critic":"critic-b","units":[d["units"][0]["coverage_id"]]}); d["units"][0].update({"wave":2,"owner":"critic-a","proposed_by":"critic-a"})'
mutate owner_not_in_wave 'd["units"][0]["owner"]="hunter-z"'
mutate unit_not_listed_in_wave 'd["waves"][0]["units"].remove(d["units"][0]["coverage_id"])'
mutate complete_with_planned_unit 'd["units"][9].update({"status":"planned","unresolved_reason":None}); recount()'
mutate complete_with_missing_cell 'd["units"].pop(); recount()'
mutate incomplete_without_reason 'd["run"]["status"]="incomplete"'
mutate complete_with_reason 'd["run"]["incomplete_reason"]="still hunting"'
mutate summary_mismatch 'd["summary"]["units"]=99'
mutate traversal_path 'd["units"][0]["reviewed_paths"][0]="../etc/passwd"'
mutate absolute_path 'd["units"][0]["reviewed_paths"][0]="/etc/passwd"'
mutate architecture_digest_mismatch 'd["run"]["architecture"]["sha256"]="0"*64'
mutate carried_unknown_run 'd["units"][0]["carried_from"]={"run_id":"run-000","prior_status":"covered","source_changed":False}'
mutate carried_changed_source_without_checks 'd["run"]["prior_runs"]=["run-000"]; d["units"][0]["carried_from"]={"run_id":"run-000","prior_status":"covered","source_changed":True}; d["units"][0]["checks"]=[]'
mutate carried_changed_source_without_wave 'd["run"]["prior_runs"]=["run-000"]; d["units"][0]["carried_from"]={"run_id":"run-000","prior_status":"covered","source_changed":True}; d["units"][0]["owner"]=None; d["units"][0]["wave"]=None'
mutate captured_without_hex_ref 'd["receipt_kind"]="captured_run"'
mutate hidden_field 'd["units"][0]["notes"]="extra"'

# Filesystem cases: copy the bound evidence into a fresh root and change it there.
fs_case() {
  local name="$1" expression="$2" expectation="${3:-reject}"
  rm -rf "$TMP/case"
  mkdir -p "$TMP/case/templates/agentic"
  cp -R "$ROOT/$EVIDENCE" "$TMP/case/$EVIDENCE"
  cp "$SAMPLE" "$TMP/case/templates/agentic/"
  python3 - "$TMP/case" "$EVIDENCE" "$expression" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]); evidence=root/sys.argv[2]; sample=root/"templates/agentic/security-coverage.sample.json"
d=json.loads(sample.read_text(encoding="utf-8"))
def rebind():
    d["run"]["architecture"]["sha256"]=hashlib.sha256((evidence/"architecture.md").read_bytes()).hexdigest()
exec(sys.argv[3], {"d":d,"evidence":evidence,"root":root,"os":os,"rebind":rebind})
sample.write_text(json.dumps(d), encoding="utf-8")
PY
  if python3 "$VALIDATOR" "$TMP/case/templates/agentic/security-coverage.sample.json" --evidence-root "$TMP/case" >"$TMP/case.out" 2>&1; then
    if [[ "$expectation" == reject ]]; then echo "expected coverage rejection: $name" >&2; exit 1; fi
  elif [[ "$expectation" == accept ]]; then
    echo "expected coverage acceptance: $name" >&2; cat "$TMP/case.out" >&2; exit 1
  fi
}

fs_case copied_layout 'pass' accept
fs_case architecture_too_long 'p=evidence/"architecture.md"; p.write_text(p.read_text()+"\n"+" filler"*1000); rebind()'
fs_case architecture_missing_heading 'p=evidence/"architecture.md"; p.write_text(p.read_text().replace("## Stack\n","## Stacks\n")); rebind()'
fs_case architecture_symlink 'p=evidence/"architecture.md"; q=evidence/"architecture-real.md"; os.rename(p,q); os.symlink(q,p)'
fs_case architecture_missing '(evidence/"architecture.md").unlink()'

# Target-root presence checks.
mkdir -p "$TMP/target"
python3 - "$SAMPLE" "$TMP/target" <<'PY'
import json,sys
from pathlib import Path
d=json.load(open(sys.argv[1])); root=Path(sys.argv[2]); seen=set()
def walk(v):
    if isinstance(v,str) and v.startswith(("src/","tests/")): seen.add(v)
    elif isinstance(v,list): [walk(x) for x in v]
    elif isinstance(v,dict): [walk(x) for x in v.values()]
walk(d)
for item in sorted(seen):
    p=root/item
    if item.endswith("/"): p.mkdir(parents=True, exist_ok=True)
    else: p.parent.mkdir(parents=True, exist_ok=True); p.write_text("# fixture\n")
PY
python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --target-root "$TMP/target" >/dev/null
rm "$TMP/target/src/notes/search.py"
if python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --target-root "$TMP/target" >/dev/null 2>&1; then
  echo "expected rejection for a reviewed path missing under the target root" >&2
  exit 1
fi

ln -s "$SAMPLE" "$TMP/linked.json"
set +e
python3 "$VALIDATOR" "$TMP/linked.json" --evidence-root "$ROOT" >/dev/null 2>"$TMP/linked.err"
code=$?
set -e
if [[ "$code" -ne 2 ]] || ! grep -q 'regular file, not a symlink' "$TMP/linked.err"; then
  echo "expected symlinked coverage ledger rejection with exit 2" >&2
  exit 1
fi

echo "security coverage fixtures passed"
