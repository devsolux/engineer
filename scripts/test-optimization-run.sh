#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-optimization-run.py"
SAMPLE="$ROOT/templates/agentic/optimization-run.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 -m json.tool "$ROOT/templates/agentic/optimization-run.schema.json" >/dev/null
grep -q 'actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6' "$ROOT/templates/github/optimization-attestation.yml"
grep -q 'subject-path: .engineer/optimization/trials.json' "$ROOT/templates/github/optimization-attestation.yml"
if grep -A3 '^  workflow_dispatch:' "$ROOT/templates/github/optimization-attestation.yml" | grep -q 'inputs:'; then
  echo "optimization attestation workflow must not accept caller-controlled inputs" >&2; exit 1
fi
python3 "$VALIDATOR" "$SAMPLE" --evidence-root "$ROOT" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and all(d["checks"].values()) and not d["captured_evidence"] and not d["eligible_for_promotion"]'

# Captured promotion requires a cryptographic verifier. This fake only tests exact
# CLI integration and output binding; it is not a cryptographic fixture.
python3 -c "from pathlib import Path; p=Path('$TMP/gh'); p.write_text('''#!/usr/bin/env python3
import hashlib,json,sys
assert sys.argv[1:3] == [\"attestation\",\"verify\"]
required={\"--repo\",\"--bundle\",\"--custom-trusted-root\",\"--signer-workflow\",\"--signer-digest\",\"--source-digest\",\"--source-ref\",\"--predicate-type\",\"--cert-oidc-issuer\",\"--deny-self-hosted-runners\",\"--format\"}
assert required <= set(sys.argv)
digest=hashlib.sha256(open(sys.argv[3],\"rb\").read()).hexdigest()
print(json.dumps([{\"verificationResult\":{\"statement\":{\"subject\":[{\"digest\":{\"sha256\":digest}}],\"predicateType\":\"https://slsa.dev/provenance/v1\"}}}]))
'''); p.chmod(0o755); Path('$TMP/bundle.jsonl').write_text('{}\n'); Path('$TMP/trusted-root.jsonl').write_text('{}\n')"
python3 -c "import hashlib,json; h=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest(); r=json.load(open('$SAMPLE')); v=json.load(open('$ROOT/templates/agentic/optimization-evidence/variants.json')); json.dump(v,open('$TMP/variants.json','w'),sort_keys=True); r['change'].update(variant_bundle_path='variants.json',variant_bundle_sha256=h('$TMP/variants.json')); a=json.load(open('$ROOT/templates/agentic/optimization-evidence/trials.json')); a['capture_kind']='captured_run'; a['runner']='sealed-eval-runner-v1'; binding={k:r[k] for k in ('change','claim','environment','datasets','gates')}; a['experiment_binding_sha256']=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest(); json.dump(a,open('$TMP/captured.json','w'),sort_keys=True); r['evidence'].update(capture_kind='captured_run',runner='sealed-eval-runner-v1',path='captured.json',sha256=h('$TMP/captured.json'),attestation={'provider':'github_sigstore','repository':'devsolux/engineer','signer_workflow':'github.com/devsolux/engineer/.github/workflows/optimization-eval.yml','signer_digest':'a'*40,'source_digest':'b'*40,'source_ref':'refs/heads/main','predicate_type':'https://slsa.dev/provenance/v1','deny_self_hosted_runners':True,'bundle_path':'bundle.jsonl','bundle_sha256':h('$TMP/bundle.jsonl'),'trusted_root_path':'trusted-root.jsonl','trusted_root_sha256':h('$TMP/trusted-root.jsonl')}); r['decision']='promote'; json.dump(r,open('$TMP/promote.json','w'))"
python3 -c "import json; p=json.load(open('$TMP/promote.json')); p['decision']='reject'; p['evidence']['attestation']=None; json.dump(p,open('$TMP/captured-reject.json','w'))"
python3 "$VALIDATOR" "$TMP/captured-reject.json" --evidence-root "$TMP" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and not d["captured_evidence"] and not d["eligible_for_promotion"]'
if python3 "$VALIDATOR" "$TMP/promote.json" --evidence-root "$TMP" >/dev/null 2>&1; then
  echo "expected captured promotion without cryptographic verification to fail" >&2; exit 1
fi
if PATH="$TMP:$PATH" python3 "$VALIDATOR" "$TMP/promote.json" --evidence-root "$TMP" --verify-attestation >/dev/null 2>&1; then
  echo "expected captured promotion without external trust policy to fail" >&2; exit 1
fi
PATH="$TMP:$PATH" python3 "$VALIDATOR" "$TMP/promote.json" --evidence-root "$TMP" --verify-attestation --attestation-policy "$ROOT/templates/agentic/optimization-attestation-policy.sample.json" --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and d["captured_evidence"] and d["eligible_for_promotion"]'

invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$SAMPLE')); $mutation; json.dump(p,open('$TMP/$name.json','w'))"
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected invalid optimization run to fail: $name" >&2; exit 1
  fi
}
invalid_case multiple_changes "p['change']['changed_variables'].append('tool description')"
invalid_case dataset_leak "p['datasets']['holdout']=['cap_resume']"
invalid_case too_few_trials "p['results']['candidate']=p['results']['candidate'][1:]"
invalid_case unpaired_trial "p['results']['candidate'][0]['trial_id']='other'"
invalid_case mismatched_infrastructure "p['results']['candidate'][0]['infrastructure_error']=True"
invalid_case holdout_regression "[(t.update(passed=False)) for t in p['results']['candidate'] if t['suite']=='holdout']"
invalid_case safety_regression "p['results']['candidate'][-1]['safety_pass']=False"
invalid_case cost_regression "[(t.update(cost_usd=2.0)) for t in p['results']['candidate']]"
invalid_case latency_regression "[(t.update(latency_ms=500)) for t in p['results']['candidate']]"
invalid_case self_review "p['trace_review']['reviewer_role']=p['trace_review']['optimizer_role']"
invalid_case optimizer_role_drift "p['trace_review']['optimizer_role']='different-optimizer'"
invalid_case fake_trace_review "p['trace_review']['reviewed_candidate_trials']=['fake/a/t1','fake/b/t2','fake/c/t3']"
invalid_case grader_gaming "p['trace_review']['grader_gaming_found']=True"
invalid_case false_promotion "[(t.update(quality=0.1)) for t in p['results']['candidate'] if t['suite']=='capability']"
invalid_case unsupported_generalization "p['claim']['generalization_claimed']=True; p['claim']['estimand']='task_population_performance'"
invalid_case nonfinite_gate "p['gates']['max_latency_p95_increase_percent']=float('nan')"
invalid_case nonfinite_result "p['results']['candidate'][0]['cost_usd']=float('inf')"

evidence_invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import hashlib,json; h=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest(); r=json.load(open('$SAMPLE')); v=json.load(open('$ROOT/templates/agentic/optimization-evidence/variants.json')); json.dump(v,open('$TMP/$name-variants.json','w'),sort_keys=True); r['change'].update(variant_bundle_path='$name-variants.json',variant_bundle_sha256=h('$TMP/$name-variants.json')); a=json.load(open('$ROOT/templates/agentic/optimization-evidence/trials.json')); binding={k:r[k] for k in ('change','claim','environment','datasets','gates')}; a['experiment_binding_sha256']=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest(); $mutation; json.dump(a,open('$TMP/$name-evidence.json','w'),sort_keys=True); r['evidence'].update(path='$name-evidence.json',sha256=h('$TMP/$name-evidence.json')); json.dump(r,open('$TMP/$name.json','w'))"
  if python3 "$VALIDATOR" "$TMP/$name.json" --evidence-root "$TMP" >/dev/null 2>&1; then
    echo "expected invalid optimization evidence to fail: $name" >&2; exit 1
  fi
}
evidence_invalid_case holdout_visible "a['protocol']['optimizer_saw_holdout_results']=True"
evidence_invalid_case unblinded_grader "a['trials'][0]['grader']['blind']=False"
evidence_invalid_case mismatched_seed "a['trials'][1]['seed']=999"
evidence_invalid_case biased_order "[(t.update(run_order=1 if t['variant']=='baseline' else 2)) for t in a['trials']]"
evidence_invalid_case self_report_mismatch "a['trials'][0]['grader']['quality']=0.99"
evidence_invalid_case swapped_variant_bindings "a['variant_bindings']['baseline'],a['variant_bindings']['candidate']=a['variant_bindings']['candidate'],a['variant_bindings']['baseline']"
evidence_invalid_case forged_variant_binding "a['variant_bindings']['baseline']['variant_sha256']='0'*64"
evidence_invalid_case mismatched_prompt_binding "a['variant_bindings']['candidate']['prompt_sha256']='0'*64"
evidence_invalid_case missing_variant_binding "a['variant_bindings'].pop('candidate')"
evidence_invalid_case extra_variant_binding "a['variant_bindings']['shadow']=a['variant_bindings']['baseline']"

variant_invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import hashlib,json; h=lambda p:hashlib.sha256(open(p,'rb').read()).hexdigest(); c=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest(); r=json.load(open('$SAMPLE')); v=json.load(open('$ROOT/templates/agentic/optimization-evidence/variants.json')); $mutation; json.dump(v,open('$TMP/$name-variants.json','w'),sort_keys=True); r['change'].update(variant_bundle_path='$name-variants.json',variant_bundle_sha256=h('$TMP/$name-variants.json')); a=json.load(open('$ROOT/templates/agentic/optimization-evidence/trials.json')); a['variant_bindings']={n:{'variant_sha256':c(v[n]),**{f'{k}_sha256':c(v[n][k]) for k in ('prompt','context','tool','loop','model','grader','environment')}} for n in ('baseline','candidate')}; binding={k:r[k] for k in ('change','claim','environment','datasets','gates')}; a['experiment_binding_sha256']=hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest(); json.dump(a,open('$TMP/$name-trials.json','w'),sort_keys=True); r['evidence'].update(path='$name-trials.json',sha256=h('$TMP/$name-trials.json')); json.dump(r,open('$TMP/$name.json','w'))"
  if python3 "$VALIDATOR" "$TMP/$name.json" --evidence-root "$TMP" >/dev/null 2>&1; then
    echo "expected invalid optimization variant bundle to fail: $name" >&2; exit 1
  fi
}
variant_invalid_case hidden_tool_change "v['candidate']['tool']['manifest_sha256']='1'*64"
variant_invalid_case hidden_loop_change "v['candidate']['loop']['max_steps']=99"
variant_invalid_case no_actual_change "v['candidate']['prompt']['checkpoint_instruction']=v['baseline']['prompt']['checkpoint_instruction']"
variant_invalid_case version_drift "v['candidate']['version']='coding-agent-v3'"
variant_invalid_case environment_drift "v['candidate']['environment']['resource_class']='8cpu-16gb'"

attestation_invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$TMP/promote.json')); $mutation; json.dump(p,open('$TMP/att-$name.json','w'))"
  if PATH="$TMP:$PATH" python3 "$VALIDATOR" "$TMP/att-$name.json" --evidence-root "$TMP" --verify-attestation --attestation-policy "$ROOT/templates/agentic/optimization-attestation-policy.sample.json" >/dev/null 2>&1; then
    echo "expected invalid optimization attestation to fail: $name" >&2; exit 1
  fi
}
attestation_invalid_case self_hosted_allowed "p['evidence']['attestation']['deny_self_hosted_runners']=False"
attestation_invalid_case signer_fork "p['evidence']['attestation']['signer_workflow']='github.com/attacker/engineer/.github/workflows/optimization-eval.yml'"
attestation_invalid_case source_ref_short "p['evidence']['attestation']['source_ref']='main'"
attestation_invalid_case bundle_hash_forged "p['evidence']['attestation']['bundle_sha256']='0'*64"
attestation_invalid_case wrong_predicate "p['evidence']['attestation']['predicate_type']='https://example.com/predicate/v1'"

policy_invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$ROOT/templates/agentic/optimization-attestation-policy.sample.json')); $mutation; json.dump(p,open('$TMP/policy-$name.json','w'))"
  if PATH="$TMP:$PATH" python3 "$VALIDATOR" "$TMP/promote.json" --evidence-root "$TMP" --verify-attestation --attestation-policy "$TMP/policy-$name.json" >/dev/null 2>&1; then
    echo "expected invalid external attestation policy to fail: $name" >&2; exit 1
  fi
}
policy_invalid_case attacker_repository "p['repository']='attacker/engineer'; p['signer_workflow']='github.com/attacker/engineer/.github/workflows/optimization-eval.yml'"
policy_invalid_case mutable_signer "p['signer_digest']='main'"
policy_invalid_case wildcard_ref "p['allowed_source_refs']=['refs/heads/*']"
policy_invalid_case self_hosted_trusted "p['deny_self_hosted_runners']=False"
policy_invalid_case wrong_issuer "p['oidc_issuer']='https://issuer.example'"

invalid_case unsafe_evidence_path "p['evidence']['path']='../../outside.json'"
invalid_case unsafe_variant_path "p['change']['variant_bundle_path']='../../variants.json'"
invalid_case forged_capture_kind "p['evidence']['capture_kind']='captured_run'; p['decision']='promote'"
echo "optimization run fixtures passed"
