#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-skill-eval-capture.py"
SAMPLE="$ROOT/templates/agentic/skill-eval-capture.sample.json"
# Standalone clean-checkout runs must not depend on prior suites.
mkdir -p "$ROOT/.engineer"
TMP="$(mktemp -d "$ROOT/.engineer/capture-manifest-test.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

python3 "$VALIDATOR" "$SAMPLE" --root "$ROOT" >/dev/null

mutate() {
  local name="$1" expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); exec(sys.argv[3],{'d':d}); json.dump(d,open(sys.argv[2],'w'),indent=2)
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" --root "$ROOT" >/dev/null 2>&1; then
    echo "expected skill eval capture-manifest rejection: $name" >&2
    exit 1
  fi
}

mutate job_hash_forgery 'd["job"]["sha256"]="0"*64'
mutate identity_drift 'd["scenario_id"]=13'
mutate host_binding_drift 'd["host_binding"]["help_output_sha256"]="0"*64'
mutate skill_binding_drift 'd["skill_binding"]["sha256"]="0"*64'
mutate runtime_not_supplied 'd["skill_binding"]["runtime_supplied"]=False'
mutate unresolved_skill 'd["skill_binding"]["unresolved_marker_absent"]=False'
mutate activation_not_confirmed 'd["skill_binding"]["activation_confirmed"]=False'
mutate activation_mode_drift 'd["skill_binding"]["activation_mode"]="implicit"'
mutate activation_probe_forgery 'd["skill_binding"]["activation_probe_sha256"]="0"*64'
mutate activation_invocation_drift 'd["skill_binding"]["invocation"]="/wrong"'
mutate activation_mechanism_drift 'd["skill_binding"]["mechanism"]="prompt_only"'
mutate live_not_reverified 'd["host_binding"]["live_reverified"]=False'
mutate artifact_escape 'd["artifacts"][0]["path"]="../../outside.md"'
mutate artifact_hash_forgery 'd["artifacts"][0]["sha256"]="0"*64'
mutate artifact_size_forgery 'd["artifacts"][1]["bytes"]+=1'
mutate duplicate_artifact 'd["artifacts"][2]["kind"]="trace"'
mutate timeout_success 'd["execution"]["timed_out"]=True'
mutate logical_command_forgery 'd["execution"]["logical_command_sha256"]="0"*64'
mutate behavioral_self_pass 'd["assessment"]["behavioral_pass"]=True'
mutate grading_skipped 'd["assessment"]["grading_required"]=False'
mutate missing_limitation 'd["limitations"].pop()'
mutate false_captured_origin 'd["capture_kind"]="captured_run"'

ln -s "$ROOT/templates/fixtures/skill-eval/output.md" "$TMP/linked-output.md"
python3 - "$SAMPLE" "$TMP/linked-output.json" "$TMP/linked-output.md" "$ROOT" <<'PY'
import json, os, sys
sample, out, linked, root = sys.argv[1:]
d = json.load(open(sample))
next(item for item in d["artifacts"] if item["kind"] == "output")["path"] = os.path.relpath(linked, root)
json.dump(d, open(out, "w"), indent=2)
PY
if python3 "$VALIDATOR" "$TMP/linked-output.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "symlinked capture artifact unexpectedly passed" >&2
  exit 1
fi

mkdir "$TMP/real-artifacts"
cp "$ROOT/templates/fixtures/skill-eval/output.md" "$TMP/real-artifacts/output.md"
ln -s real-artifacts "$TMP/linked-artifacts"
python3 - "$SAMPLE" "$TMP/linked-parent.json" "$TMP/linked-artifacts/output.md" "$ROOT" <<'PY'
import json, os, sys
sample, out, linked, root = sys.argv[1:]
d = json.load(open(sample))
next(item for item in d["artifacts"] if item["kind"] == "output")["path"] = os.path.relpath(linked, root)
json.dump(d, open(out, "w"), indent=2)
PY
if python3 "$VALIDATOR" "$TMP/linked-parent.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "capture artifact beneath a symlinked parent unexpectedly passed" >&2
  exit 1
fi

python3 - "$SAMPLE" "$TMP/no-probe-output.md" "$TMP/no-probe.json" "$ROOT" <<'PY'
import hashlib,json,os,sys
sample,outfile,out,root=sys.argv[1:]
open(outfile,'w').write('No activation marker here.\n')
d=json.load(open(sample)); a=next(x for x in d['artifacts'] if x['kind']=='output'); body=open(outfile,'rb').read()
a.update(path=os.path.relpath(outfile,root),sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
json.dump(d,open(out,'w'),indent=2)
PY
if python3 "$VALIDATOR" "$TMP/no-probe.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "missing sealed activation marker unexpectedly passed" >&2
  exit 1
fi

python3 - "$SAMPLE" "$TMP/secret.log" "$TMP/secret.json" "$ROOT" <<'PY'
import hashlib,json,os,sys
sample,secret,out,root=sys.argv[1:]
open(secret,'w').write('authorization=Bearer sk-ant-'+'x'*40+'\n')
d=json.load(open(sample))
a=next(x for x in d['artifacts'] if x['kind']=='log')
a['path']=os.path.relpath(secret,root)
body=open(secret,'rb').read()
a['sha256']=hashlib.sha256(body).hexdigest()
a['bytes']=len(body)
json.dump(d,open(out,'w'),indent=2)
PY
if python3 "$VALIDATOR" "$TMP/secret.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "secret-bearing capture artifact unexpectedly passed" >&2
  exit 1
fi

# A hash-consistent job must still pass the canonical job compiler.
python3 - "$ROOT/templates/agentic/skill-eval-job.sample.json" "$TMP/invalid-job.json" "$SAMPLE" "$TMP/invalid-job-manifest.json" "$ROOT" <<'PY'
import hashlib,json,os,sys
job_source,job_out,sample,out,root=sys.argv[1:]
job=json.load(open(job_source)); job['permissions']['network']='allow'; json.dump(job,open(job_out,'w'),indent=2)
d=json.load(open(sample)); d['job']['path']=os.path.relpath(job_out,root)
d['job']['sha256']=hashlib.sha256(open(job_out,'rb').read()).hexdigest(); json.dump(d,open(out,'w'),indent=2)
PY
if python3 "$VALIDATOR" "$TMP/invalid-job-manifest.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "hash-consistent invalid capture job unexpectedly passed" >&2
  exit 1
fi

echo "skill eval capture manifest fixtures passed"
