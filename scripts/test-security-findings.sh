#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-security-findings.py"
SAMPLE="$ROOT/templates/agentic/security-findings.sample.json"
COVERAGE="$ROOT/templates/agentic/security-coverage.sample.json"
EVIDENCE="templates/agentic/security-audit-evidence"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["valid"] and not d["errors"] and not d["gates"], d'

# Document-only mutations. C, N and R name the confirmed, needs_validation and
# rejected records of the sample; COV is the bound coverage ledger (read only).
write_mutation() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$COVERAGE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1], encoding="utf-8")); COV=json.load(open(sys.argv[2], encoding="utf-8"))
C=next(r for r in d["records"] if r["verdict"]=="confirmed")
N=next(r for r in d["records"] if r["verdict"]=="needs_validation")
R=next(r for r in d["records"] if r["verdict"]=="rejected")
exec(sys.argv[4], {"d":d,"C":C,"N":N,"R":R,"COV":COV}); json.dump(d,open(sys.argv[3],"w",encoding="utf-8"))
PY
}

mutate() {
  local name="$1" expression="$2"
  write_mutation "$name" "$expression"
  if python3 "$VALIDATOR" "$TMP/$name.json" --evidence-root "$ROOT" >/dev/null 2>&1; then
    echo "expected findings rejection: $name" >&2
    exit 1
  fi
}

accept() {
  local name="$1" expression="$2"
  write_mutation "$name" "$expression"
  if ! python3 "$VALIDATOR" "$TMP/$name.json" --evidence-root "$ROOT" >"$TMP/$name.out" 2>&1; then
    echo "expected findings acceptance: $name" >&2
    cat "$TMP/$name.out" >&2
    exit 1
  fi
}

accept carried_and_reverified 'd["run"]["prior_runs"]=["run-000"]; C["carried_from"]={"run_id":"run-000","prior_verdict":"confirmed","reverified":True}'
accept materially_replaced_with_independent_verifier 'C["verification"]["materially_replaced"]=True; C["verification"]["replacement_verifier"]="verifier-c"'
accept sandbox_unavailable_without_local_evidence 'd["run"]["sandbox"]["available"]=False; d["run"]["sandbox"]["unavailable_reason"]="no OS sandbox on this host; local execution skipped"'

mutate fingerprint_mismatch 'C["root_cause"]["symbol"]="other_symbol"'
mutate fingerprint_duplicate 'N["root_cause"]=dict(C["root_cause"]); N["attack_class"]=C["attack_class"]; N["fingerprint"]=C["fingerprint"]'
mutate unsorted_records 'd["records"].reverse()'
mutate unknown_verdict 'C["verdict"]="probable"'
mutate confirmed_without_severity 'del C["severity"]'
mutate overall_above_impact 'C["severity"]["impact"]="medium"; C["severity"]["overall"]="high"'
mutate confirmed_with_blockers 'C["blockers"]=N["blockers"]'
mutate trace_missing_sink 'C["trace"]=C["trace"][:2]'
mutate trace_wrong_stage_order 'C["trace"][1],C["trace"][2]=C["trace"][2],C["trace"][1]'
mutate trace_not_from_entrypoint 'C["trace"][0]["stage"]="propagation"'
mutate confirmed_without_evidence 'C["evidence"]=[]'
mutate confirmed_without_conditions 'C["conditions"]=[]'
mutate confirmed_low_confidence 'C["confidence"]="low"'
mutate needs_validation_with_severity 'N["severity"]=C["severity"]'
mutate needs_validation_without_blocker 'N["blockers"]=[]'
mutate needs_validation_without_plan 'N["validation_plan"]={"local":[],"owner_observed":[]}'
mutate rejected_without_reason 'R["rejection"]["reason"]=""'
mutate rejected_with_severity 'R["severity"]=C["severity"]'
mutate rejected_by_someone_else 'R["rejection"]["refuted_by"]="verifier-c"'
mutate hunter_equals_verifier 'C["verification"]["verifier"]=C["verification"]["hunter"]'
mutate reviewer_equals_hunter 'C["verification"]["record_reviewer"]=C["verification"]["hunter"]'
mutate confirmed_without_reviewer 'C["verification"]["record_reviewer"]=None'
mutate replaced_without_verifier 'C["verification"]["materially_replaced"]=True'
mutate replaced_by_original_verifier 'C["verification"]["materially_replaced"]=True; C["verification"]["replacement_verifier"]=C["verification"]["verifier"]'
mutate verified_outside_run 'C["verification"]["verified_at"]="2026-10-22T13:00:00Z"'
mutate refutation_not_attempted 'C["verification"]["verifier_attempted_refutation"]=False'
mutate unknown_coverage_id 'C["coverage_ids"]=["cov-000000000000"]'
mutate candidate_unit_without_record 'd["records"]=[r for r in d["records"] if r["verdict"]!="rejected"]; d["summary"]["rejected"]=0'
mutate confirmed_on_covered_unit 'C["coverage_ids"]=[u["coverage_id"] for u in COV["units"] if u["status"]=="covered"][:1]; R["coverage_ids"].append(COV["units"][4]["coverage_id"])'
mutate ledger_digest_mismatch 'd["run"]["coverage"]["sha256"]="0"*64'
mutate ledger_run_id_mismatch 'd["run"]["run_id"]="run-002"'
mutate architecture_digest_mismatch 'd["run"]["architecture"]["sha256"]="0"*64'
mutate evidence_digest_mismatch 'C["evidence"][0]["sha256"]="0"*64'
mutate evidence_bytes_mismatch 'C["evidence"][0]["bytes"]+=1'
mutate evidence_traversal 'C["evidence"][0]["path"]="../../../etc/passwd"'
mutate evidence_absolute 'C["evidence"][0]["path"]="/etc/passwd"'
mutate local_execution_without_sandbox 'd["run"]["sandbox"]["available"]=False; d["run"]["sandbox"]["unavailable_reason"]="no sandbox"; C["evidence"][0]["kind"]="local_execution"'
mutate live_probe 'd["run"]["safety"]["live_systems_probed"]=True'
mutate real_principals 'd["run"]["safety"]["principals"]="real"'
mutate real_secrets 'd["run"]["safety"]["secrets"]="production"'
mutate sandbox_with_network 'd["run"]["sandbox"]["network"]="egress"'
mutate credential_in_summary 'C["evidence"][0]["summary"]="token sk-"+"abcdefghijklmnop1234"'
mutate jwt_in_document 'C["title"]="eyJ"+"a"*12+".eyJ"+"b"*12+"."+"c"*12'
mutate bearer_in_document 'N["boundary"]["input"]="Authorization: Bearer "+"x9"*12'
mutate non_fixture_url 'N["boundary"]["input"]="https://203.0.113.10/attachments"'
mutate complete_with_reason 'd["run"]["incomplete_reason"]="still going"'
mutate incomplete_without_reason 'd["run"]["status"]="incomplete"'
mutate ended_before_started 'd["run"]["ended_at"]="2026-10-22T07:00:00Z"'
mutate summary_mismatch 'd["summary"]["confirmed"]=2'
mutate clean_flag_wrong 'd["summary"]["clean"]=True'
mutate carried_not_reverified 'd["run"]["prior_runs"]=["run-000"]; C["carried_from"]={"run_id":"run-000","prior_verdict":"confirmed","reverified":False}'
mutate carried_unknown_run 'C["carried_from"]={"run_id":"run-000","prior_verdict":"confirmed","reverified":True}'
mutate budget_without_reserve 'd["run"]["budget"]["reserved"]["critics"]=0'
mutate budget_reserved_after_hunting 'd["run"]["budget"]["reserved_before_hunting"]=False'
mutate hunting_ate_reserve 'd["run"]["budget"]["spent"]["hunting"]=200'
mutate captured_without_hex_ref 'd["receipt_kind"]="captured_run"'
mutate wrong_mode 'd["run"]["mode"]="guidance"'
mutate hidden_record_field 'C["exploit"]="never"'

# Filesystem cases: copy ledger and evidence into a fresh root and change them there.
fs_case() {
  local name="$1" expression="$2" expectation="${3:-reject}"
  rm -rf "$TMP/case"
  mkdir -p "$TMP/case/templates/agentic"
  cp -R "$ROOT/$EVIDENCE" "$TMP/case/$EVIDENCE"
  cp "$COVERAGE" "$SAMPLE" "$TMP/case/templates/agentic/"
  python3 - "$TMP/case" "$EVIDENCE" "$expression" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]); evidence=root/sys.argv[2]
findings_path=root/"templates/agentic/security-findings.sample.json"
coverage_path=root/"templates/agentic/security-coverage.sample.json"
d=json.loads(findings_path.read_text(encoding="utf-8")); cov=json.loads(coverage_path.read_text(encoding="utf-8"))
C=next(r for r in d["records"] if r["verdict"]=="confirmed")
N=next(r for r in d["records"] if r["verdict"]=="needs_validation")
R=next(r for r in d["records"] if r["verdict"]=="rejected")
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rebind_evidence(rec):
    p=evidence/rec["evidence"][0]["path"]; rec["evidence"][0]["sha256"]=sha(p); rec["evidence"][0]["bytes"]=p.stat().st_size
def write_coverage():
    coverage_path.write_text(json.dumps(cov,indent=2)+"\n",encoding="utf-8"); d["run"]["coverage"]["sha256"]=sha(coverage_path)
exec(sys.argv[3], {"d":d,"cov":cov,"C":C,"N":N,"R":R,"evidence":evidence,"root":root,"os":os,"sha":sha,"rebind_evidence":rebind_evidence,"write_coverage":write_coverage})
findings_path.write_text(json.dumps(d), encoding="utf-8")
PY
  if python3 "$VALIDATOR" "$TMP/case/templates/agentic/security-findings.sample.json" --evidence-root "$TMP/case" >"$TMP/case.out" 2>&1; then
    if [[ "$expectation" == reject ]]; then echo "expected findings rejection: $name" >&2; exit 1; fi
  elif [[ "$expectation" == accept ]]; then
    echo "expected findings acceptance: $name" >&2; cat "$TMP/case.out" >&2; exit 1
  fi
}

fs_case copied_layout 'pass' accept
fs_case clean_run '
for u in cov["units"]:
    if u["status"]=="candidate": u["status"]="covered"; u["candidate_fingerprints"]=[]
cov["summary"]["by_status"]["covered"]+=cov["summary"]["by_status"]["candidate"]; cov["summary"]["by_status"]["candidate"]=0
write_coverage()
d["records"]=[]; d["hardening_notes"]=[]
d["summary"]={"confirmed":0,"needs_validation":0,"rejected":0,"hardening_notes":0,"clean":True}
' accept
fs_case clean_run_with_candidate_left 'd["records"]=[]; d["hardening_notes"]=[]; d["summary"]={"confirmed":0,"needs_validation":0,"rejected":0,"hardening_notes":0,"clean":True}'
fs_case ledger_invalid 'cov["waves"][0]["critic"]="hunter-a"; write_coverage()'
fs_case ledger_different_architecture 'cov["run"]["architecture"]["sha256"]="0"*64; write_coverage()'
fs_case evidence_symlink 'p=evidence/C["evidence"][0]["path"]; q=p.with_name("real.txt"); os.rename(p,q); os.symlink(q,p)'
fs_case evidence_too_large 'p=evidence/C["evidence"][0]["path"]; p.write_bytes(b"x"*(1024*1024+1)); rebind_evidence(C)'
fs_case evidence_missing '(evidence/C["evidence"][0]["path"]).unlink()'
fs_case private_key_in_evidence_file 'p=evidence/C["evidence"][0]["path"]; p.write_text("-----BEGIN "+"PRIVATE KEY-----\nMIIEfixture\n-----END "+"PRIVATE KEY-----\n"); rebind_evidence(C)'
fs_case bearer_in_report 'p=evidence/"REPORT.md"; p.write_text(p.read_text()+"\nAuthorization: Bearer "+"q7"*12+"\n")'
fs_case report_missing '(evidence/"REPORT.md").unlink()'
fs_case artifact_root_symlink 'real=root/"real-evidence"; os.rename(evidence, real); os.symlink(real, evidence)'

# Target-root presence checks.
mkdir -p "$TMP/target"
python3 - "$SAMPLE" "$COVERAGE" "$TMP/target" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[3]); seen=set()
def walk(v):
    if isinstance(v,str) and v.startswith(("src/","tests/")): seen.add(v.split("::")[0])
    elif isinstance(v,list): [walk(x) for x in v]
    elif isinstance(v,dict): [walk(x) for x in v.values()]
for path in sys.argv[1:3]: walk(json.load(open(path)))
for item in sorted(seen):
    p=root/item
    if item.endswith("/"): p.mkdir(parents=True, exist_ok=True)
    else: p.parent.mkdir(parents=True, exist_ok=True); p.write_text("# fixture\n")
PY
python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --target-root "$TMP/target" >/dev/null
rm "$TMP/target/src/notes/service.py"
if python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --target-root "$TMP/target" >/dev/null 2>&1; then
  echo "expected rejection for a trace path missing under the target root" >&2
  exit 1
fi

ln -s "$SAMPLE" "$TMP/linked.json"
set +e
python3 "$VALIDATOR" "$TMP/linked.json" --evidence-root "$ROOT" >/dev/null 2>"$TMP/linked.err"
code=$?
set -e
if [[ "$code" -ne 2 ]] || ! grep -q 'regular file, not a symlink' "$TMP/linked.err"; then
  echo "expected symlinked findings rejection with exit 2" >&2
  exit 1
fi

# Remediation receipt (--remediated). C, N and R name the sample's records by their original
# verdicts; E is the receipt's one entry. The findings digest is rebound to the findings file
# under test before the expression runs, so only the expression's change is under test.
REMEDIATION="$ROOT/templates/agentic/security-remediation.sample.json"
python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --remediated "$REMEDIATION" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["valid"] and not d["errors"] and not d["gates"], d'

write_remediation() {
  local name="$1" expression="$2" findings="$3"
  python3 - "$REMEDIATION" "$SAMPLE" "$findings" "$TMP/rem-$name.json" "$expression" <<'PY'
import hashlib,json,sys
from pathlib import Path
d=json.load(open(sys.argv[1], encoding="utf-8")); sample=json.load(open(sys.argv[2], encoding="utf-8"))
C=next(r for r in sample["records"] if r["verdict"]=="confirmed")
N=next(r for r in sample["records"] if r["verdict"]=="needs_validation")
R=next(r for r in sample["records"] if r["verdict"]=="rejected")
E=d["entries"][0]
d["findings"]["sha256"]=hashlib.sha256(Path(sys.argv[3]).read_bytes()).hexdigest()
exec(sys.argv[5], {"d":d,"C":C,"N":N,"R":R,"E":E}); json.dump(d,open(sys.argv[4],"w",encoding="utf-8"))
PY
}

rem_mutate() {
  local name="$1" expression="$2" findings="${3:-$SAMPLE}"
  write_remediation "$name" "$expression" "$findings"
  python3 "$VALIDATOR" "$findings" --evidence-root "$ROOT" --remediated "$TMP/rem-$name.json" --json >"$TMP/rem.out" 2>&1 || true
  if ! python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert not d["valid"] and any(m.startswith("remediation") for m in d["errors"]+d["gates"]), d' "$TMP/rem.out" 2>/dev/null; then
    echo "expected remediation rejection: $name" >&2
    cat "$TMP/rem.out" >&2
    exit 1
  fi
}

rem_accept() {
  local name="$1" expression="$2" findings="${3:-$SAMPLE}"
  write_remediation "$name" "$expression" "$findings"
  if ! python3 "$VALIDATOR" "$findings" --evidence-root "$ROOT" --remediated "$TMP/rem-$name.json" >"$TMP/rem.out" 2>&1; then
    echo "expected remediation acceptance: $name" >&2
    cat "$TMP/rem.out" >&2
    exit 1
  fi
}

# Findings variants: N promoted to a second confirmed record (same root cause, unit and
# evidence), and C remediated by a directory path.
python3 - "$SAMPLE" "$TMP" <<'PY'
import copy,json,sys
sample=json.load(open(sys.argv[1], encoding="utf-8"))
d=copy.deepcopy(sample)
N=next(r for r in d["records"] if r["verdict"]=="needs_validation")
del N["blockers"], N["validation_plan"]
N["verdict"]="confirmed"
N["severity"]={"likelihood":"medium","impact":"high","overall":"medium"}
N["remediation"]={"summary":"resolve the host and refuse private, loopback, and link-local addresses before the request","layer":"outbound HTTP client","paths":["src/notes/attachments.py"],"regression_test":None}
d["summary"].update(confirmed=2, needs_validation=0)
json.dump(d, open(f"{sys.argv[2]}/two-confirmed.json","w",encoding="utf-8"))
d=copy.deepcopy(sample)
next(r for r in d["records"] if r["verdict"]=="confirmed")["remediation"]["paths"]=["src/notes"]
json.dump(d, open(f"{sys.argv[2]}/directory-paths.json","w",encoding="utf-8"))
PY
for variant in two-confirmed directory-paths; do
  python3 "$VALIDATOR" "$TMP/$variant.json" --evidence-root "$ROOT" >/dev/null
done
SECOND='S=dict(E, fingerprint=N["fingerprint"], layer="outbound HTTP client", changed_paths=["src/notes/attachments.py"]); d["not_fixed"]=[x for x in d["not_fixed"] if x["fingerprint"]!=N["fingerprint"]]'

rem_accept mitigated_declared 'E["outcome"]="mitigated"; E["mitigation"]={"owner":"notes service owner","expiry":"2026-12-01","follow_up":"tracked issue for the repository owner filter","detection":"alert when GET /notes/{id} returns another owner row in the canary"}'
rem_accept confirmed_deferred 'd["entries"]=[]; d["not_fixed"].append({"fingerprint":C["fingerprint"],"verdict":"confirmed","disposition":"deferred","reason":"the owner moved this fix to the next change window"})'
rem_accept severity_order "$SECOND"'; d["entries"]=[E,S]' "$TMP/two-confirmed.json"
rem_accept directory_remediation_path 'E["changed_paths"]=["src/notes/repository.py","src/notes/service.py"]' "$TMP/directory-paths.json"

rem_mutate severity_order_reversed "$SECOND"'; d["entries"]=[S,E]' "$TMP/two-confirmed.json"
rem_mutate findings_invalid 'pass' "$TMP/fingerprint_mismatch.json"
rem_mutate findings_digest_mismatch 'd["findings"]["sha256"]="0"*64'
rem_mutate findings_run_id_mismatch 'd["findings"]["run_id"]="run-002"'
rem_mutate receipt_kind_mismatch 'd["receipt_kind"]="captured_run"'
rem_mutate unknown_fingerprint 'E["fingerprint"]="sa1-0000000000000000"'
rem_mutate fixes_needs_validation 'E["fingerprint"]=N["fingerprint"]; d["not_fixed"]=[x for x in d["not_fixed"] if x["fingerprint"]!=N["fingerprint"]]+[{"fingerprint":C["fingerprint"],"verdict":"confirmed","disposition":"deferred","reason":"queued"}]'
rem_mutate fixes_rejected 'E["fingerprint"]=R["fingerprint"]; d["not_fixed"]=[x for x in d["not_fixed"] if x["fingerprint"]!=R["fingerprint"]]+[{"fingerprint":C["fingerprint"],"verdict":"confirmed","disposition":"deferred","reason":"queued"}]'
rem_mutate duplicate_entry 'd["entries"].append(dict(E))'
rem_mutate fixed_and_deferred 'd["not_fixed"].append({"fingerprint":C["fingerprint"],"verdict":"confirmed","disposition":"deferred","reason":"queued"})'
rem_mutate record_unaccounted 'd["not_fixed"]=[x for x in d["not_fixed"] if x["verdict"]!="needs_validation"]'
rem_mutate needs_validation_skipped 'next(x for x in d["not_fixed"] if x["verdict"]=="needs_validation")["disposition"]="skipped"'
rem_mutate rejected_handed_back 'next(x for x in d["not_fixed"] if x["verdict"]=="rejected")["disposition"]="handed_back"'
rem_mutate verdict_mislabeled 'next(x for x in d["not_fixed"] if x["verdict"]=="needs_validation")["verdict"]="rejected"'
rem_mutate not_fixed_without_reason 'd["not_fixed"][0]["reason"]=""'
rem_mutate changed_path_outside_remediation 'E["changed_paths"].append("src/notes/service.py")'
rem_mutate changed_paths_empty 'E["changed_paths"]=[]'
rem_mutate changed_path_traversal 'E["changed_paths"]=["../outside.py"]'
rem_mutate layer_mismatch 'E["layer"]="api handler"'
rem_mutate regression_test_missing 'E["regression_test"]=None'
rem_mutate regression_test_absolute 'E["regression_test"]["path"]="/tmp/test_notes.py"'
rem_mutate regression_test_never_failed 'E["regression_test"]["failed_before_fix"]["exit_code"]=0'
rem_mutate regression_test_still_failing 'E["regression_test"]["passed_after_fix"]["exit_code"]=1'
rem_mutate regression_test_commands_differ 'E["regression_test"]["passed_after_fix"]["command"]="python3 -m pytest"'
rem_mutate verification_empty 'E["verification"]=[]'
rem_mutate verification_failed 'E["verification"][1]["exit_code"]=1'
rem_mutate exit_code_boolean 'E["verification"][0]["exit_code"]=False'
rem_mutate unknown_outcome 'E["outcome"]="fixed"'
rem_mutate mitigated_undeclared 'E["outcome"]="mitigated"'
rem_mutate mitigated_without_detection 'E["outcome"]="mitigated"; E["mitigation"]={"owner":"o","expiry":"2026-12-01","follow_up":"issue","detection":""}'
rem_mutate fixed_with_mitigation 'E["mitigation"]={"owner":"o","expiry":"2026-12-01","follow_up":"issue","detection":"alert"}'
rem_mutate credential_in_command 'E["verification"][0]["command"]="API_KEY=sk-"+"abcdefghijklmnop1234"+" python3 -m pytest"'
rem_mutate non_fixture_url 'd["not_fixed"][0]["reason"]="owner check at https://203.0.113.10/egress"'
rem_mutate hidden_entry_field 'E["patch"]="diff"'
rem_mutate hidden_root_field 'd["approved"]=True'

# Target-root presence: the regression test file must exist under the target.
touch "$TMP/target/src/notes/service.py"
python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --target-root "$TMP/target" --remediated "$REMEDIATION" >/dev/null
rm "$TMP/target/tests/test_notes_isolation.py"
if python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --target-root "$TMP/target" --remediated "$REMEDIATION" >/dev/null 2>&1; then
  echo "expected rejection for a regression test missing under the target root" >&2
  exit 1
fi

ln -s "$REMEDIATION" "$TMP/linked-remediation.json"
printf '{"schema_version": 1,' >"$TMP/truncated-remediation.json"
for input in linked-remediation truncated-remediation; do
  set +e
  python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --remediated "$TMP/$input.json" >/dev/null 2>"$TMP/$input.err"
  code=$?
  set -e
  if [[ "$code" -ne 2 ]]; then
    echo "expected exit 2 for $input" >&2
    exit 1
  fi
done
if ! grep -q 'remediation must be a regular file, not a symlink' "$TMP/linked-remediation.err"; then
  echo "symlinked remediation rejected for the wrong reason" >&2
  exit 1
fi

echo "security findings fixtures passed"
