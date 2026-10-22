#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL="$ROOT/scripts/security-ledger.py"
VALIDATOR="$ROOT/scripts/validate-security-coverage.py"
ARCHITECTURE="$ROOT/templates/agentic/security-audit-evidence/architecture.md"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

expect_refusal() {
  local fragment="$1"
  shift
  if "$@" >"$TMP/out" 2>"$TMP/err"; then
    echo "expected refusal: $*" >&2
    exit 1
  fi
  if ! grep -q -- "$fragment" "$TMP/err"; then
    echo "refused for the wrong reason (wanted '$fragment'): $*" >&2
    cat "$TMP/err" >&2
    exit 1
  fi
}

unit_ids() { python3 -c 'import json,sys; print("\n".join(u["coverage_id"] for u in json.load(open(sys.argv[1]))["units"]))' "$1"; }
unit_field() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); u=next(x for x in d["units"] if x["coverage_id"]==sys.argv[2]); print(json.dumps(u[sys.argv[3]]))' "$1" "$2" "$3"; }
run_field() { python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["run"][sys.argv[2]]))' "$1" "$2"; }

# ---- init: cross product of the dimensions, every unit planned ---------------
RUN1="$TMP/run-001"
mkdir -p "$RUN1" "$TMP/nogit"
cp "$ARCHITECTURE" "$RUN1/architecture.md"
cat >"$TMP/dims.json" <<'JSON'
{
  "surfaces": [{"id": "http-api", "ref": "src/api/routes.py", "kind": "http"}],
  "boundaries": [
    {"id": "anonymous-to-member", "from": "anonymous", "to": "member", "strongest_visible_control": "session cookie check"},
    {"id": "member-to-owner", "from": "member", "to": "owner", "strongest_visible_control": "ownership check"}
  ],
  "subsystems": [{"id": "notes", "paths": ["src/notes/"]}],
  "attack_classes": ["injection", "access_control"]
}
JSON
REF1="$(python3 -c 'print("a"*40)')"
python3 "$TOOL" init --dimensions "$TMP/dims.json" --run-id run-001 --target-name fixture-notes-service --source-ref "$REF1" --profile quick --architecture architecture.md --receipt-kind illustrative_fixture --output "$RUN1/coverage.json" >"$TMP/out"
grep -q '"units": 4' "$TMP/out"
python3 "$VALIDATOR" "$RUN1/coverage.json" --evidence-root "$RUN1" >/dev/null
IDS=($(unit_ids "$RUN1/coverage.json"))
[[ "${#IDS[@]}" -eq 4 ]]
python3 - "$RUN1/coverage.json" <<'PY'
import hashlib,json,sys
d=json.load(open(sys.argv[1]))
for u in d["units"]:
    expected="cov-"+hashlib.sha256(f'{u["surface"]}|{u["boundary"]}|{u["subsystem"]}|{u["attack_class"]}'.encode()).hexdigest()[:12]
    assert u["coverage_id"]==expected and u["status"]=="planned" and u["owner"] is None and u["wave"] is None, u
assert d["summary"]["by_status"]["planned"]==4 and d["summary"]["expected_cells"]==4 and d["run"]["status"]=="incomplete"
PY
expect_refusal 'refusing to overwrite' python3 "$TOOL" init --dimensions "$TMP/dims.json" --run-id run-001 --target-name fixture --source-ref "$REF1" --architecture architecture.md --receipt-kind illustrative_fixture --output "$RUN1/coverage.json"
expect_refusal 'need --source-ref' python3 "$TOOL" init --dimensions "$TMP/dims.json" --run-id run-009 --target-name fixture --architecture architecture.md --target-root "$TMP/nogit" --output "$RUN1/other.json"
[[ ! -e "$RUN1/other.json" ]]

# ---- assign: waves, hunters, critic independence ------------------------------
python3 "$TOOL" assign "$RUN1/coverage.json" --wave 1 --hunter hunter-a --critic critic-a "${IDS[0]}" "${IDS[1]}" >/dev/null
python3 "$TOOL" assign "$RUN1/coverage.json" --wave 1 --hunter hunter-b --critic critic-a "${IDS[2]}" >/dev/null
[[ "$(unit_field "$RUN1/coverage.json" "${IDS[0]}" status)" == '"in_progress"' ]]
[[ "$(unit_field "$RUN1/coverage.json" "${IDS[2]}" owner)" == '"hunter-b"' ]]
expect_refusal 'must not hunt' python3 "$TOOL" assign "$RUN1/coverage.json" --wave 1 --hunter critic-a --critic critic-a "${IDS[3]}"
expect_refusal 'already has critic' python3 "$TOOL" assign "$RUN1/coverage.json" --wave 1 --hunter hunter-c --critic critic-z "${IDS[3]}"
expect_refusal 'only planned, blocked, or deferred' python3 "$TOOL" assign "$RUN1/coverage.json" --wave 1 --hunter hunter-a --critic critic-a "${IDS[0]}"
expect_refusal 'unknown coverage unit' python3 "$TOOL" assign "$RUN1/coverage.json" --wave 1 --hunter hunter-a --critic critic-a cov-000000000000
python3 "$VALIDATOR" "$RUN1/coverage.json" --evidence-root "$RUN1" >/dev/null

# ---- promote: regular-file, size, JSON, content, and assigned-unit checks ------
result() {
  python3 - "$1" "$2" "$3" "$4" "${IDS[@]}" <<'PY'
import hashlib,json,sys
out,agent,wave,expr=sys.argv[1:5]; ids=sys.argv[5:]
def fp(attack_class,path,symbol,sink): return "sa1-"+hashlib.sha256(f"{attack_class}|{path}|{symbol or ''}|{sink or ''}".encode()).hexdigest()[:16]
def check(name,path="src/notes/repository.py"): return {"id":name,"method":"source","description":"traced the handler to its check","paths":[path],"result_fingerprint":hashlib.sha256(name.encode()).hexdigest()[:16]}
def candidate(cid):
    f=fp("access_control","src/notes/repository.py","get_note","db.execute")
    return {"fingerprint":f,"title":"member reads a foreign note","attack_class":"access_control","domain":"data_isolation","root_cause":{"path":"src/notes/repository.py","symbol":"get_note","sink":"db.execute","note":"no owner filter"},"coverage_ids":[cid],"boundary":{"principal":"member","input":"note id","intended_control":"ownership check","crossed":"member-to-owner","result":"foreign note returned"},"trace":[{"stage":"entrypoint","path":"src/api/routes.py","symbol":"get_note_handler","line":42,"note":"entry"},{"stage":"sink","path":"src/notes/repository.py","symbol":"get_note","line":31,"note":"sink"}],"evidence":[],"conditions":[{"kind":"authentication_level","description":"any member session"}]}
r={"units":[],"candidates":[],"hardening":[],"uncovered":[]}
exec(expr,{"r":r,"ids":ids,"check":check,"candidate":candidate,"fp":fp})
json.dump(r,open(out,"w"))
PY
}
result "$TMP/hunter-a.json" hunter-a 1 'c=candidate(ids[1]); r["candidates"]=[c]; r["units"]=[{"coverage_id":ids[0],"status":"covered","reviewed_paths":["src/notes/repository.py"],"checks":[check("inj-a")],"unresolved_reason":None,"candidate_fingerprints":[]},{"coverage_id":ids[1],"status":"candidate","reviewed_paths":["src/notes/repository.py"],"checks":[check("ac-a")],"unresolved_reason":None,"candidate_fingerprints":[c["fingerprint"]]}]'
python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-a.json" --agent hunter-a --wave 1 >"$TMP/out"
grep -q '"copied_to"' "$TMP/out"
cmp "$TMP/hunter-a.json" "$RUN1/agents/hunter-a.json"
[[ "$(unit_field "$RUN1/coverage.json" "${IDS[0]}" status)" == '"covered"' ]]
[[ "$(unit_field "$RUN1/coverage.json" "${IDS[1]}" status)" == '"candidate"' ]]
python3 "$VALIDATOR" "$RUN1/coverage.json" --evidence-root "$RUN1" >/dev/null

cp "$RUN1/coverage.json" "$TMP/before.json"
ln -s "$TMP/hunter-a.json" "$TMP/linked-result.json"
expect_refusal 'regular file, not a symlink' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/linked-result.json" --agent hunter-a --wave 1
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d["padding"]="x"*(2*1024*1024); json.dump(d,open(sys.argv[2],"w"))' "$TMP/hunter-a.json" "$TMP/oversize.json"
expect_refusal 'exceeds' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/oversize.json" --agent hunter-a --wave 1
printf '{"schema_version": 1,' >"$TMP/broken.json"
expect_refusal 'not valid JSON' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/broken.json" --agent hunter-a --wave 1
result "$TMP/hunter-b-steal.json" hunter-b 1 'r["units"]=[{"coverage_id":ids[0],"status":"covered","reviewed_paths":["src/notes/repository.py"],"checks":[check("x")],"unresolved_reason":None,"candidate_fingerprints":[]}]'
expect_refusal 'not assigned to hunter-b' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-steal.json" --agent hunter-b --wave 1
result "$TMP/hunter-b-wave2.json" hunter-b 2 'pass'
expect_refusal 'not a hunter of wave 2' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-wave2.json" --agent hunter-b --wave 2
result "$TMP/hunter-z.json" hunter-z 1 'pass'
expect_refusal 'not a hunter of wave 1' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-z.json" --agent hunter-z --wave 1
result "$TMP/hunter-b-badfp.json" hunter-b 1 'c=candidate(ids[2]); c["fingerprint"]="sa1-0000000000000000"; r["candidates"]=[c]; r["units"]=[{"coverage_id":ids[2],"status":"candidate","reviewed_paths":["src/notes/repository.py"],"checks":[check("y")],"unresolved_reason":None,"candidate_fingerprints":["sa1-0000000000000000"]}]'
expect_refusal 'fingerprint does not match' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-badfp.json" --agent hunter-b --wave 1
result "$TMP/hunter-b-orphan.json" hunter-b 1 'r["units"]=[{"coverage_id":ids[2],"status":"candidate","reviewed_paths":["src/notes/repository.py"],"checks":[check("y")],"unresolved_reason":None,"candidate_fingerprints":[fp("injection","src/notes/search.py","search",None)]}]'
expect_refusal 'without a matching candidate' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-orphan.json" --agent hunter-b --wave 1
result "$TMP/hunter-b-secret.json" hunter-b 1 'r["hardening"]=[{"title":"token sk-"+"abcdefghijklmnop1234","location":{"path":"src/config.py","symbol":None},"note":"n","layer_preventing_attack":"l","coverage_ids":[ids[2]]}]'
expect_refusal 'credential-shaped' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-secret.json" --agent hunter-b --wave 1
result "$TMP/hunter-b-badstatus.json" hunter-b 1 'r["units"]=[{"coverage_id":ids[2],"status":"in_progress","reviewed_paths":[],"checks":[],"unresolved_reason":None,"candidate_fingerprints":[]}]'
expect_refusal 'status must be one of' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-badstatus.json" --agent hunter-b --wave 1
result "$TMP/hunter-a-again.json" hunter-a 1 'pass'
expect_refusal 'already exists' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-a-again.json" --agent hunter-a --wave 1
cmp "$RUN1/coverage.json" "$TMP/before.json"

result "$TMP/hunter-b.json" hunter-b 1 'r["uncovered"]=[{"coverage_id":ids[2],"description":"the sandbox was unavailable for the local check"},{"coverage_id":None,"description":"a search endpoint outside the declared surfaces"}]'
python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b.json" --agent hunter-b --wave 1 >"$TMP/out"
grep -q 'a search endpoint outside the declared surfaces' "$TMP/out"
result "$TMP/hunter-b-legacy.json" hunter-b 1 'r["agent"]="hunter-b"; r["wave"]=1'
expect_refusal 'exactly units, candidates, hardening, and uncovered' python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-b-legacy.json" --agent hunter-b --wave 1
[[ "$(unit_field "$RUN1/coverage.json" "${IDS[2]}" status)" == '"blocked"' ]]

# ---- finish: complete only when every cell is terminal --------------------------
expect_refusal 'planned or in_progress' python3 "$TOOL" finish "$RUN1/coverage.json"
[[ "$(run_field "$RUN1/coverage.json" status)" == '"incomplete"' ]]
python3 "$TOOL" finish "$RUN1/coverage.json" --incomplete "wave 2 has not run" >/dev/null
python3 "$TOOL" assign "$RUN1/coverage.json" --wave 2 --hunter hunter-c --critic critic-b "${IDS[2]}" "${IDS[3]}" >/dev/null
result "$TMP/hunter-c.json" hunter-c 2 'r["units"]=[{"coverage_id":i,"status":"covered","reviewed_paths":["src/notes/repository.py"],"checks":[check("c-"+i)],"unresolved_reason":None,"candidate_fingerprints":[]} for i in (ids[2],ids[3])]'
python3 "$TOOL" promote "$RUN1/coverage.json" "$TMP/hunter-c.json" --agent hunter-c --wave 2 >/dev/null
python3 "$TOOL" finish "$RUN1/coverage.json" >/dev/null
[[ "$(run_field "$RUN1/coverage.json" status)" == '"complete"' ]]
python3 "$VALIDATOR" "$RUN1/coverage.json" --evidence-root "$RUN1" >/dev/null

# ---- gap without a git repository: reported, every shared unit treated as changed
RUN2="$TMP/run-002"
mkdir -p "$RUN2" "$TMP/nogit-target/src/notes"
cp "$ARCHITECTURE" "$RUN2/architecture.md"
python3 "$TOOL" init --dimensions "$TMP/dims.json" --run-id run-002 --target-name fixture-notes-service --source-ref "$REF1" --profile quick --architecture architecture.md --receipt-kind illustrative_fixture --output "$RUN2/coverage.json" >/dev/null
python3 "$TOOL" gap "$RUN2/coverage.json" --prior "$RUN1" --target-root "$TMP/nogit-target" >"$TMP/out"
grep -q 'not possible' "$TMP/out"
python3 - "$RUN2/coverage.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["run"]["prior_runs"]==["run-001"]
for u in d["units"]:
    assert u["carried_from"]["run_id"]=="run-001" and u["carried_from"]["source_changed"] is True and u["status"]=="planned", u
PY
python3 "$VALIDATOR" "$RUN2/coverage.json" --evidence-root "$RUN2" --target-root "$TMP/nogit-target" >/dev/null
ln -s "$RUN1/coverage.json" "$TMP/linked-ledger.json"
expect_refusal 'regular file, not a symlink' python3 "$TOOL" finish "$TMP/linked-ledger.json"
ln -s "$RUN1" "$TMP/linked-prior"
expect_refusal 'must not be a symlink' python3 "$TOOL" gap "$RUN2/coverage.json" --prior "$TMP/linked-prior" --target-root "$TMP/nogit-target"

# ---- gap with a git repository: changed subsystem re-hunted, untouched carried ---
if command -v git >/dev/null 2>&1; then
  TARGET="$TMP/target"
  mkdir -p "$TARGET/src/notes" "$TARGET/src/api"
  printf 'def get_note(): pass\n' >"$TARGET/src/notes/repository.py"
  printf 'def route(): pass\n' >"$TARGET/src/api/routes.py"
  GIT=(git -C "$TARGET" -c user.name=fixture -c user.email=fixture@example.test -c commit.gpgsign=false -c init.defaultBranch=main)
  "${GIT[@]}" init -q
  "${GIT[@]}" add -A
  "${GIT[@]}" commit -q -m "fixture baseline"
  REF_OLD="$("${GIT[@]}" rev-parse HEAD)"
  cat >"$TMP/dims-git.json" <<'JSON'
{
  "surfaces": [{"id": "http-api", "ref": "src/api/routes.py", "kind": "http"}],
  "boundaries": [{"id": "member-to-owner", "from": "member", "to": "owner", "strongest_visible_control": "ownership check"}],
  "subsystems": [{"id": "notes", "paths": ["src/notes/"]}, {"id": "api", "paths": ["src/api/"]}],
  "attack_classes": ["access_control"]
}
JSON
  RUN3="$TMP/run-003"
  mkdir -p "$RUN3"
  cp "$ARCHITECTURE" "$RUN3/architecture.md"
  python3 "$TOOL" init --dimensions "$TMP/dims-git.json" --run-id run-003 --target-name fixture --architecture architecture.md --target-root "$TARGET" --output "$RUN3/coverage.json" >"$TMP/out"
  grep -q "\"source_ref\": \"$REF_OLD\"" "$TMP/out"
  IDS=($(unit_ids "$RUN3/coverage.json"))
  python3 "$TOOL" assign "$RUN3/coverage.json" --wave 1 --hunter hunter-a --critic critic-a "${IDS[@]}" --target-root "$TARGET" >/dev/null
  result "$TMP/git-hunter-a.json" hunter-a 1 'r["units"]=[{"coverage_id":i,"status":"covered","reviewed_paths":[p],"checks":[check("c-"+i,p)],"unresolved_reason":None,"candidate_fingerprints":[]} for i,p in zip(ids,["src/notes/repository.py","src/api/routes.py"])]'
  python3 "$TOOL" promote "$RUN3/coverage.json" "$TMP/git-hunter-a.json" --agent hunter-a --wave 1 --target-root "$TARGET" >/dev/null
  python3 "$TOOL" finish "$RUN3/coverage.json" --target-root "$TARGET" >/dev/null
  printf 'def get_note(owner_id): pass\n' >"$TARGET/src/notes/repository.py"
  "${GIT[@]}" commit -q -am "change the notes subsystem"
  RUN4="$TMP/run-004"
  mkdir -p "$RUN4"
  cp "$ARCHITECTURE" "$RUN4/architecture.md"
  python3 "$TOOL" init --dimensions "$TMP/dims-git.json" --run-id run-004 --target-name fixture --architecture architecture.md --target-root "$TARGET" --output "$RUN4/coverage.json" >/dev/null
  python3 "$TOOL" gap "$RUN4/coverage.json" --prior "$RUN3" --target-root "$TARGET" >"$TMP/out"
  grep -q '1 changed file' "$TMP/out"
  [[ "$(unit_field "$RUN4/coverage.json" "${IDS[0]}" status)" == '"planned"' ]]
  [[ "$(unit_field "$RUN4/coverage.json" "${IDS[0]}" carried_from)" == *'"source_changed": true'* ]]
  [[ "$(unit_field "$RUN4/coverage.json" "${IDS[1]}" status)" == '"covered"' ]]
  [[ "$(unit_field "$RUN4/coverage.json" "${IDS[1]}" carried_from)" == *'"source_changed": false'* ]]
  [[ "$(unit_field "$RUN4/coverage.json" "${IDS[1]}" owner)" == 'null' ]]
  python3 "$VALIDATOR" "$RUN4/coverage.json" --evidence-root "$RUN4" --target-root "$TARGET" >/dev/null
else
  echo "git unavailable; skipped the source-change gap case"
fi

echo "security ledger tool fixtures passed"
