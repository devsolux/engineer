#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATOR="$ROOT/scripts/validate-skill-eval-run.py"
SAMPLE="$ROOT/templates/agentic/skill-eval-run.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cd "$ROOT"
python3 "$VALIDATOR" "$SAMPLE" >/dev/null

python3 - "$SAMPLE" "$TMP/promotion.json" <<'PY'
import copy
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
base = data["trials"][0]
data["decision"] = "promote"
data["run_kind"] = "captured_run"
data["baseline_run_id"] = "engineer-1.11.0-holdout-001"
data["dataset"].update({
    "split": "holdout",
    "visibility": "private",
    "scenario_ids": [101, 102, 103],
    "selection_notes": "Sequestered promotion fixture.",
})
data["trials"] = []
for scenario_id in data["dataset"]["scenario_ids"]:
    for trial_number in range(1, 4):
        trial = copy.deepcopy(base)
        trial["scenario_id"] = scenario_id
        trial["trial_id"] = f"{scenario_id}-{trial_number}"
        data["trials"].append(trial)
data["summary"].update({"behavior_trials": 9, "behavior_passes": 9})
data["comparison"] = {
    "baseline_run_id": data["baseline_run_id"],
    "paired_environment": True,
    "scenario_ids_match": True,
    "baseline_pass_rate": 0.8888888888888888,
    "candidate_pass_rate": 1.0,
    "baseline_infrastructure_error_rate": 0.0,
    "candidate_infrastructure_error_rate": 0.0,
    "per_scenario_regressions": 0,
    "safety_regressions": 0,
    "cost_delta_pct": 2.0,
    "cost_budget_pct": 5.0,
    "latency_p95_delta_pct": 1.0,
    "latency_budget_pct": 5.0,
}
data["promotion"] = {"eligible": True, "reason": "All paired promotion gates pass."}
json.dump(data, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
python3 "$VALIDATOR" "$TMP/promotion.json" >/dev/null

mutate() {
  local name="$1"
  local expression="$2"
  python3 - "$SAMPLE" "$TMP/$name.json" "$expression" <<'PY'
import json
import sys

source, target, expression = sys.argv[1:]
data = json.load(open(source, encoding="utf-8"))
exec(expression, {"data": data})
json.dump(data, open(target, "w", encoding="utf-8"), indent=2)
PY
  if python3 "$VALIDATOR" "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected rejection: $name" >&2
    exit 1
  fi
}

mutate bad_hash 'data["trials"][0]["artifacts"][0]["sha256"] = "0" * 64'
mutate stale_skill_hash 'data["environment"]["skill_sha256"] = "0" * 64'
mutate illustrative_promotion 'data["decision"] = "promote"; data["promotion"]["eligible"] = True; data["baseline_run_id"] = "baseline-1"'
mutate self_review 'data["review"]["independent_reviewer"] = data["review"]["tested_agent"]'
mutate false_summary 'data["summary"]["behavior_passes"] = 0'
mutate graded_infra 'data["trials"][0]["status"] = "infrastructure_error"'
mutate missing_trajectory 'data["trials"][0]["graders"] = data["trials"][0]["graders"][:1]'
mutate model_without_calibration 'data["trials"][0]["graders"][0]["type"] = "model"; data["review"]["model_graders_used"] = True'
mutate public_promotion 'data["decision"] = "promote"; data["promotion"]["eligible"] = True; data["baseline_run_id"] = "baseline-1"'
mutate contaminated_promotion 'data["decision"] = "promote"; data["promotion"]["eligible"] = True; data["baseline_run_id"] = "baseline-1"; data["dataset"]["visibility"] = "private"; data["dataset"]["split"] = "holdout"; data["dataset"]["contamination_found"] = True'

echo "skill eval run fixtures passed"
