#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-capability-promotion.py"
SAMPLE="$ROOT/templates/agentic/capability-promotion.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$SAMPLE" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["valid"] and not d["errors"] and not d["gates"]'

mutate() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1], encoding="utf-8")); exec(sys.argv[3], {"d":d}); json.dump(d,open(sys.argv[2],"w",encoding="utf-8"))
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected capability promotion rejection: $name" >&2
    exit 1
  fi
}

mutate one_occurrence 'd["signals"]["occurrences"]=d["signals"]["occurrences"][:1]; d["candidate"]["consequence"]="medium"'
mutate duplicate_occurrence 'd["signals"]["occurrences"][1]["project_id"]=d["signals"]["occurrences"][0]["project_id"]; d["signals"]["occurrences"][1]["task_id"]=d["signals"]["occurrences"][0]["task_id"]'
mutate missing_engineer 'd["catalog"]["candidates"]=d["catalog"]["candidates"][1:]'
mutate no_skill_creator 'd["catalog"]["skill_creator_loaded"]=False'
mutate duplicate_owner 'd["catalog"]["candidates"][0]["fit"]="equal"'
mutate missing_option 'd["options"]=d["options"][:-1]'
mutate high_router_risk 'next(x for x in d["options"] if x["choice"]=="new-skill")["routing_risk"]="high"'
mutate no_negative_eval 'd["evaluation"]["cases"]=[x for x in d["evaluation"]["cases"] if x["kind"]!="negative"]'
mutate recursive_creation 'd["decision"]["recursive_creation"]=True'
mutate false_nonmutation 'd["decision"]["skill_mutation"]=False'
mutate unauthorized_apply 'd["decision"]["phase"]="apply"; d["review"]["approved"]=True'
mutate unauthorized_install 'd["decision"]["phase"]="install"; d["authority"]["allowed_destinations"]=[d["decision"]["target"]]; d["review"]["approved"]=True'
mutate self_review 'd["review"]["checker"]=d["review"]["maker"]'
mutate unstable_job 'd["candidate"]["stable_outputs"]=False'
mutate relabeled_capture 'd["receipt_kind"]="captured_assessment"'

python3 - "$SAMPLE" "$TMP" <<'PY'
import hashlib,json,pathlib,sys
sample=pathlib.Path(sys.argv[1]); root=pathlib.Path(sys.argv[2]); d=json.loads(sample.read_text())
def write(name,obj):
    path=root/name; path.write_text(json.dumps(obj,sort_keys=True),encoding="utf-8")
    return {"path":name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
signals=write("signals.json",{"candidate_id":d["candidate"]["id"],**d["signals"]})
catalog=write("catalog.json",{"candidate_id":d["candidate"]["id"],"skill_creator_loaded":d["catalog"]["skill_creator_loaded"],"candidates":d["catalog"]["candidates"]})
d["catalog"]["inventory_sha256"]=catalog["sha256"]
authority=write("authority.json",{"candidate_id":d["candidate"]["id"],**d["authority"]})
decision_sha=hashlib.sha256(json.dumps(d["decision"],sort_keys=True,separators=(",",":")).encode()).hexdigest()
review=write("review.json",{"candidate_id":d["candidate"]["id"],"decision_sha256":decision_sha,**d["review"]})
d["receipt_kind"]="captured_assessment"; d["evidence"]={"signals":signals,"catalog":catalog,"authority":authority,"review":review}
(root/"captured.json").write_text(json.dumps(d),encoding="utf-8")
PY
python3 "$VALIDATOR" "$TMP/captured.json" --evidence-root "$TMP" >/dev/null

cp "$TMP/signals.json" "$TMP/signals-before.json"
printf '\n' >>"$TMP/signals.json"
if python3 "$VALIDATOR" "$TMP/captured.json" --evidence-root "$TMP" >/dev/null 2>&1; then
  echo "expected tampered captured signal rejection" >&2
  exit 1
fi
mv "$TMP/signals-before.json" "$TMP/signals.json"

python3 - "$TMP/captured.json" "$TMP/stale-review.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); d["decision"]["reason"]="changed after review"; json.dump(d,open(sys.argv[2],"w"))
PY
if python3 "$VALIDATOR" "$TMP/stale-review.json" --evidence-root "$TMP" >/dev/null 2>&1; then
  echo "expected stale captured review rejection" >&2
  exit 1
fi

mv "$TMP/catalog.json" "$TMP/catalog-real.json"
ln -s "$TMP/catalog-real.json" "$TMP/catalog.json"
if python3 "$VALIDATOR" "$TMP/captured.json" --evidence-root "$TMP" >/dev/null 2>&1; then
  echo "expected symlinked captured catalog rejection" >&2
  exit 1
fi

ln -s "$SAMPLE" "$TMP/linked.json"
if python3 "$VALIDATOR" "$TMP/linked.json" >/dev/null 2>&1; then
  echo "expected symlinked capability receipt rejection" >&2
  exit 1
fi

echo "capability promotion fixtures passed"
