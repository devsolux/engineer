#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-agentic-contract.py"
SAMPLE="$ROOT/templates/agentic/execution-contract.sample.json"
TRAJECTORY="$ROOT/templates/agentic/trajectory.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 -m json.tool "$ROOT/templates/agentic/execution-contract.schema.json" >/dev/null
python3 "$VALIDATOR" "$SAMPLE" >/dev/null
python3 "$ROOT/scripts/validate-agentic-trajectory.py" "$TRAJECTORY" --contract "$SAMPLE" >/dev/null

invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$SAMPLE')); $mutation; json.dump(p,open('$TMP/$name.json','w'))"
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected invalid fixture to fail: $name" >&2; exit 1
  fi
}
invalid_case orphan_requirement "p['requirements'].append({'id':'req_orphan','text':'orphan','risk':'low'})"
invalid_case dangling_acceptance "p['plan'][0]['acceptance_ids']=['ac_missing']"
invalid_case missing_oracle "p['acceptance'][0]['oracles']=[]"
invalid_case oracle_escape "p['acceptance'][0]['oracles'][0]['artifact']='../secret.json'"
invalid_case oracle_operator "p['acceptance'][0]['oracles'][0]['operator']='execute'"
invalid_case oracle_not_evidence "p['acceptance'][0]['oracles'][0]['artifact']='other.json'"
invalid_case unbounded_loop "p['loop']['max_steps']=0"
invalid_case unsafe_mutation "p['tools'][1]['approval']='none'"
invalid_case no_holdout "p['prompt_optimization']['holdout_set']=p['prompt_optimization']['regression_set']"
invalid_case false_done "p['stop_conditions'].remove('evidence_artifact_written')"
invalid_case missing_security "p.pop('security')"
invalid_case tool_sink_outside_policy "p['tools'][1]['allowed_sinks']=['network']"
invalid_case malformed_tool_class "p['tools'][0]['class']=7"

invalid_trace() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$TRAJECTORY')); $mutation; json.dump(p,open('$TMP/trace-$name.json','w'))"
  if python3 "$ROOT/scripts/validate-agentic-trajectory.py" "$TMP/trace-$name.json" --contract "$SAMPLE" >/dev/null 2>&1; then
    echo "expected invalid trajectory to fail: $name" >&2; exit 1
  fi
}
invalid_trace missing_observation "p['events']=[e for e in p['events'] if not (e.get('phase')=='observe' and e.get('action_id')=='action-2')]; [e.update(seq=i+1) for i,e in enumerate(p['events'])]"
invalid_trace false_success "p['events'][-1]['verification_passed']=False"
invalid_trace missing_acceptance "p['events'][-1]['acceptance_ids']=['ac_resume']"
invalid_trace unapproved_mutation "p['events'][2]['approval']='none'"
invalid_trace undeclared_sink "p['events'][2]['output_sinks']=['network']"
invalid_trace no_checkpoint "p['events']=[e for e in p['events'] if e.get('phase')!='checkpoint']; [e.update(seq=i+1) for i,e in enumerate(p['events'])]"
invalid_trace no_progress_spiral "p['events'][7]['state_hash']='repo-b'"
invalid_trace no_stop "p['events']=p['events'][:-1]"
invalid_trace stale_checkpoint "e=p['events'].pop(8); e['state_hash']='repo-b'; p['events'].insert(6,e); [x.update(seq=i+1) for i,x in enumerate(p['events'])]"
invalid_trace observation_without_evidence "p['events'][3]['evidence']=[]"
invalid_trace observation_without_state "p['events'][3].pop('state_hash')"
invalid_trace observation_without_outcome "p['events'][3].pop('ok')"
invalid_trace checkpoint_state_drift "p['events'][8]['state_hash']='unobserved-state'"
invalid_trace unplanned_completion "p['events']=[e for e in p['events'] if not (e.get('phase')=='plan' and e.get('step_id')=='step_stop')]; [e.update(seq=i+1) for i,e in enumerate(p['events'])]"
invalid_trace undeclared_stop_reason "p['events'][-1]={'seq':10,'phase':'stop','reason':'model_felt_done'}"

ln -s "$TRAJECTORY" "$TMP/trajectory-link.json"
if python3 "$ROOT/scripts/validate-agentic-trajectory.py" "$TMP/trajectory-link.json" --contract "$SAMPLE" >/dev/null 2>&1; then
  echo "expected symlinked trajectory rejection" >&2; exit 1
fi
ln -s "$SAMPLE" "$TMP/contract-link.json"
if python3 "$ROOT/scripts/validate-agentic-trajectory.py" "$TRAJECTORY" --contract "$TMP/contract-link.json" >/dev/null 2>&1; then
  echo "expected symlinked trajectory contract rejection" >&2; exit 1
fi

python3 -c "import json; p=json.load(open('$SAMPLE')); p['security']['allowed_sinks'].append('network'); t=p['tools'][1]; t.update({'class':'external_reversible','network':'allowlist','allowed_sinks':['network']}); json.dump(p,open('$TMP/external-contract.json','w'))"
python3 -c "import json; p=json.load(open('$TRAJECTORY')); e=p['events'][2]; e.update({'input_sources':['issue_text'],'output_sinks':['network']}); json.dump(p,open('$TMP/unconfirmed-transfer.json','w'))"
python3 "$VALIDATOR" "$TMP/external-contract.json" >/dev/null
if python3 "$ROOT/scripts/validate-agentic-trajectory.py" "$TMP/unconfirmed-transfer.json" --contract "$TMP/external-contract.json" >/dev/null 2>&1; then
  echo "expected unconfirmed cross-domain transfer to fail" >&2; exit 1
fi
echo "agentic contract fixtures passed"
