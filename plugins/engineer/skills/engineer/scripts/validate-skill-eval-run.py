#!/usr/bin/env python3
"""Validate captured behavioral skill-evaluation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

HEX = set("0123456789abcdef")
STATUSES = {"success", "agent_failure", "infrastructure_error"}
GRADER_TYPES = {"code", "model", "human"}
TARGETS = {"outcome", "trajectory", "response"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_repo_path(value: Any, root: Path) -> Path | None:
    return safe_path(value, root)


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def finite_number(value: Any, minimum: float = 0) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= minimum


def validate(data: Any, root: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"]

    required = {"schema_version", "skill_name", "skill_version", "run_id", "captured_at", "run_kind", "decision", "baseline_run_id", "comparison", "environment", "dataset", "review", "trials", "summary", "promotion"}
    unknown = set(data) - required
    missing = required - set(data)
    if missing:
        errors.append(f"missing root keys: {sorted(missing)}")
    if unknown:
        errors.append(f"unknown root keys: {sorted(unknown)}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("skill_name") != "engineer":
        errors.append("skill_name must be engineer")
    if data.get("run_kind") not in {"illustrative_fixture", "captured_run"}:
        errors.append("run_kind must be illustrative_fixture or captured_run")
    for key in ("skill_version", "run_id", "captured_at"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{key} must be a non-empty string")
    decision = data.get("decision")
    if decision not in {"report_only", "reject", "promote"}:
        errors.append("decision must be report_only, reject, or promote")

    env = data.get("environment")
    env_keys = {"host", "model", "model_version", "temperature", "max_steps", "network_policy", "skill_path", "skill_sha256", "bank_path", "bank_sha256", "instructions_sha256", "tools_sha256", "fixture_sha256"}
    if not isinstance(env, dict):
        errors.append("environment must be an object")
        env = {}
    elif set(env) != env_keys:
        errors.append(f"environment keys must be exactly {sorted(env_keys)}")
    for key in ("host", "model", "model_version", "network_policy"):
        if not isinstance(env.get(key), str) or not env[key].strip():
            errors.append(f"environment.{key} must be non-empty")
    if env.get("network_policy") not in {"deny", "simulated", "allowlisted"}:
        errors.append("environment.network_policy must be deny, simulated, or allowlisted")
    if not finite_number(env.get("temperature")):
        errors.append("environment.temperature must be a finite non-negative number")
    if not isinstance(env.get("max_steps"), int) or isinstance(env.get("max_steps"), bool) or env.get("max_steps", 0) < 1:
        errors.append("environment.max_steps must be a positive integer")
    for key in ("skill_sha256", "bank_sha256", "instructions_sha256", "tools_sha256", "fixture_sha256"):
        if not is_hash(env.get(key)):
            errors.append(f"environment.{key} must be a lowercase SHA-256")
    for path_key, hash_key in (("skill_path", "skill_sha256"), ("bank_path", "bank_sha256")):
        path = safe_repo_path(env.get(path_key), root)
        if path is None or not path.is_file():
            errors.append(f"environment.{path_key} is unsafe or missing")
        elif is_hash(env.get(hash_key)) and sha256(path) != env.get(hash_key):
            errors.append(f"environment.{hash_key} does not match {env.get(path_key)}")

    dataset = data.get("dataset")
    if not isinstance(dataset, dict):
        errors.append("dataset must be an object")
        dataset = {}
    expected_dataset = {"split", "visibility", "scenario_ids", "contamination_checked", "contamination_found", "selection_notes"}
    if set(dataset) != expected_dataset:
        errors.append(f"dataset keys must be exactly {sorted(expected_dataset)}")
    if dataset.get("split") not in {"capability", "regression", "holdout", "adversarial"}:
        errors.append("dataset.split is invalid")
    if dataset.get("visibility") not in {"public", "private", "sequestered"}:
        errors.append("dataset.visibility is invalid")
    scenario_ids = dataset.get("scenario_ids")
    if not isinstance(scenario_ids, list) or not scenario_ids or any(not isinstance(x, int) or isinstance(x, bool) or x < 1 for x in scenario_ids):
        errors.append("dataset.scenario_ids must contain positive integers")
        scenario_ids = []
    elif len(set(scenario_ids)) != len(scenario_ids):
        errors.append("dataset.scenario_ids must be unique")
    for key in ("contamination_checked", "contamination_found"):
        if not isinstance(dataset.get(key), bool):
            errors.append(f"dataset.{key} must be boolean")
    if not isinstance(dataset.get("selection_notes"), str) or not dataset.get("selection_notes", "").strip():
        errors.append("dataset.selection_notes must be non-empty")

    review = data.get("review")
    if not isinstance(review, dict):
        errors.append("review must be an object")
        review = {}
    expected_review = {"tested_agent", "grader_author", "independent_reviewer", "model_graders_used", "human_calibration"}
    if set(review) != expected_review:
        errors.append(f"review keys must be exactly {sorted(expected_review)}")
    for key in ("tested_agent", "grader_author", "independent_reviewer"):
        if not isinstance(review.get(key), str) or not review[key].strip():
            errors.append(f"review.{key} must be non-empty")
    identities = [review.get("tested_agent"), review.get("grader_author"), review.get("independent_reviewer")]
    if len({x for x in identities if isinstance(x, str)}) != 3:
        errors.append("tested agent, grader author, and independent reviewer must differ")
    if not isinstance(review.get("model_graders_used"), bool):
        errors.append("review.model_graders_used must be boolean")
    calibration = review.get("human_calibration")
    if review.get("model_graders_used"):
        if not isinstance(calibration, dict):
            errors.append("model graders require human_calibration")
        else:
            if not isinstance(calibration.get("sample_size"), int) or calibration.get("sample_size", 0) < 5:
                errors.append("human_calibration.sample_size must be at least 5")
            if not finite_number(calibration.get("agreement")) or calibration.get("agreement", 2) > 1 or calibration.get("agreement", 0) < 0.8:
                errors.append("human_calibration.agreement must be between 0.8 and 1")
            if not isinstance(calibration.get("reviewer"), str) or calibration.get("reviewer") in {review.get("tested_agent"), review.get("grader_author")}:
                errors.append("human calibration requires an independent reviewer")
    elif calibration is not None:
        errors.append("human_calibration must be null when model graders are unused")

    trials = data.get("trials")
    if not isinstance(trials, list) or not trials:
        errors.append("trials must be a non-empty array")
        trials = []
    seen_trials: set[str] = set()
    actual = {"success": 0, "agent_failure": 0, "infrastructure_error": 0}
    model_seen = False
    for index, trial in enumerate(trials):
        label = f"trials[{index}]"
        if not isinstance(trial, dict):
            errors.append(f"{label} must be an object")
            continue
        expected_trial = {"scenario_id", "trial_id", "status", "latency_ms", "cost_usd", "artifacts", "graders"}
        if set(trial) != expected_trial:
            errors.append(f"{label} keys must be exactly {sorted(expected_trial)}")
        scenario_id = trial.get("scenario_id")
        if scenario_id not in scenario_ids:
            errors.append(f"{label}.scenario_id is not declared in dataset")
        trial_id = trial.get("trial_id")
        if not isinstance(trial_id, str) or not trial_id:
            errors.append(f"{label}.trial_id must be non-empty")
        elif trial_id in seen_trials:
            errors.append(f"duplicate trial_id: {trial_id}")
        else:
            seen_trials.add(trial_id)
        status = trial.get("status")
        if status not in STATUSES:
            errors.append(f"{label}.status is invalid")
        else:
            actual[status] += 1
        for key in ("latency_ms", "cost_usd"):
            if not finite_number(trial.get(key)):
                errors.append(f"{label}.{key} must be finite and non-negative")

        artifacts = trial.get("artifacts")
        artifact_paths: set[str] = set()
        artifact_kinds: set[str] = set()
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{label}.artifacts must be non-empty")
            artifacts = []
        for art in artifacts:
            if not isinstance(art, dict) or set(art) != {"kind", "path", "sha256"}:
                errors.append(f"{label} artifact must have kind, path, and sha256")
                continue
            if art.get("kind") not in {"output", "trace", "state", "log"}:
                errors.append(f"{label} artifact kind is invalid")
            else:
                artifact_kinds.add(art["kind"])
            path = safe_repo_path(art.get("path"), root)
            if path is None or not path.is_file():
                errors.append(f"{label} artifact path is unsafe or missing: {art.get('path')}")
            else:
                artifact_paths.add(art["path"])
                if not is_hash(art.get("sha256")) or sha256(path) != art.get("sha256"):
                    errors.append(f"{label} artifact hash mismatch: {art.get('path')}")
        if "output" not in artifact_kinds or "trace" not in artifact_kinds:
            errors.append(f"{label} requires output and trace artifacts")

        graders = trial.get("graders")
        if status == "infrastructure_error":
            if graders not in ([], None):
                errors.append(f"{label} infrastructure errors must not receive behavior grades")
            continue
        if not isinstance(graders, list) or not graders:
            errors.append(f"{label}.graders must be non-empty for behavior trials")
            continue
        targets: set[str] = set()
        passed_values: list[bool] = []
        for grader in graders:
            if not isinstance(grader, dict):
                errors.append(f"{label} grader must be an object")
                continue
            expected_grader = {"id", "type", "target", "version", "score", "threshold", "passed", "independent", "evidence"}
            if set(grader) != expected_grader:
                errors.append(f"{label} grader keys must be exactly {sorted(expected_grader)}")
            if grader.get("type") not in GRADER_TYPES:
                errors.append(f"{label} grader type is invalid")
            if grader.get("type") == "model":
                model_seen = True
            target = grader.get("target")
            if target not in TARGETS:
                errors.append(f"{label} grader target is invalid")
            else:
                targets.add(target)
            for key in ("id", "version"):
                if not isinstance(grader.get(key), str) or not grader[key].strip():
                    errors.append(f"{label} grader {key} must be non-empty")
            score, threshold = grader.get("score"), grader.get("threshold")
            if not finite_number(score) or not finite_number(threshold) or score > 1 or threshold > 1:
                errors.append(f"{label} grader score and threshold must be within 0..1")
            passed = grader.get("passed")
            if not isinstance(passed, bool):
                errors.append(f"{label} grader passed must be boolean")
            elif finite_number(score) and finite_number(threshold) and passed != (score >= threshold):
                errors.append(f"{label} grader passed disagrees with score threshold")
            else:
                passed_values.append(passed)
            if grader.get("independent") is not True:
                errors.append(f"{label} graders must be independent of the tested agent")
            evidence = grader.get("evidence")
            if not isinstance(evidence, list) or not evidence or any(item not in artifact_paths for item in evidence):
                errors.append(f"{label} grader evidence must reference captured artifacts")
        if "outcome" not in targets or "trajectory" not in targets:
            errors.append(f"{label} behavior trials require outcome and trajectory graders")
        derived_success = bool(passed_values) and all(passed_values)
        if (status == "success") != derived_success:
            errors.append(f"{label} status disagrees with grader results")

    if model_seen != bool(review.get("model_graders_used")):
        errors.append("review.model_graders_used disagrees with trial graders")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        summary = {}
    expected_summary = {"behavior_trials", "behavior_passes", "agent_failures", "infrastructure_errors", "pass_rate", "infrastructure_error_rate"}
    if set(summary) != expected_summary:
        errors.append(f"summary keys must be exactly {sorted(expected_summary)}")
    behavior_trials = actual["success"] + actual["agent_failure"]
    expected_values = {
        "behavior_trials": behavior_trials,
        "behavior_passes": actual["success"],
        "agent_failures": actual["agent_failure"],
        "infrastructure_errors": actual["infrastructure_error"],
    }
    for key, value in expected_values.items():
        if summary.get(key) != value:
            errors.append(f"summary.{key} must equal {value}")
    total = behavior_trials + actual["infrastructure_error"]
    expected_pass_rate = actual["success"] / behavior_trials if behavior_trials else 0
    expected_infra_rate = actual["infrastructure_error"] / total if total else 0
    for key, value in (("pass_rate", expected_pass_rate), ("infrastructure_error_rate", expected_infra_rate)):
        if not finite_number(summary.get(key)) or abs(summary.get(key, -1) - value) > 1e-9:
            errors.append(f"summary.{key} must equal {value}")

    promotion = data.get("promotion")
    if not isinstance(promotion, dict) or set(promotion) != {"eligible", "reason"}:
        errors.append("promotion must contain eligible and reason")
        promotion = {}
    if not isinstance(promotion.get("eligible"), bool) or not isinstance(promotion.get("reason"), str) or not promotion.get("reason", "").strip():
        errors.append("promotion eligibility must be boolean with a non-empty reason")
    eligible = promotion.get("eligible") is True
    comparison = data.get("comparison")
    comparison_keys = {"baseline_run_id", "paired_environment", "scenario_ids_match", "baseline_pass_rate", "candidate_pass_rate", "baseline_infrastructure_error_rate", "candidate_infrastructure_error_rate", "per_scenario_regressions", "safety_regressions", "cost_delta_pct", "cost_budget_pct", "latency_p95_delta_pct", "latency_budget_pct"}
    if comparison is not None and (not isinstance(comparison, dict) or set(comparison) != comparison_keys):
        errors.append(f"comparison must be null or contain exactly {sorted(comparison_keys)}")
    if decision == "promote" and not eligible:
        errors.append("decision promote requires promotion.eligible true")
    if eligible:
        if data.get("run_kind") != "captured_run":
            errors.append("promotion requires run_kind captured_run")
        if decision != "promote":
            errors.append("eligible promotion requires decision promote")
        if not isinstance(data.get("baseline_run_id"), str) or not data.get("baseline_run_id"):
            errors.append("promotion requires baseline_run_id")
        if not isinstance(comparison, dict):
            errors.append("promotion requires an explicit baseline comparison")
        else:
            if comparison.get("baseline_run_id") != data.get("baseline_run_id"):
                errors.append("comparison baseline_run_id must match the root baseline_run_id")
            if comparison.get("paired_environment") is not True or comparison.get("scenario_ids_match") is not True:
                errors.append("promotion requires paired environments and matching scenarios")
            for key in ("baseline_pass_rate", "candidate_pass_rate", "baseline_infrastructure_error_rate", "candidate_infrastructure_error_rate"):
                if not finite_number(comparison.get(key)) or comparison.get(key, 2) > 1:
                    errors.append(f"comparison.{key} must be within 0..1")
            if finite_number(comparison.get("baseline_pass_rate")) and finite_number(comparison.get("candidate_pass_rate")) and comparison["candidate_pass_rate"] < comparison["baseline_pass_rate"]:
                errors.append("candidate pass rate regresses the baseline")
            if finite_number(comparison.get("baseline_infrastructure_error_rate")) and finite_number(comparison.get("candidate_infrastructure_error_rate")) and comparison["candidate_infrastructure_error_rate"] > comparison["baseline_infrastructure_error_rate"]:
                errors.append("candidate infrastructure-error rate regresses the baseline")
            for key in ("per_scenario_regressions", "safety_regressions"):
                if comparison.get(key) != 0:
                    errors.append(f"comparison.{key} must be zero for promotion")
            for delta, budget in (("cost_delta_pct", "cost_budget_pct"), ("latency_p95_delta_pct", "latency_budget_pct")):
                if not finite_number(comparison.get(delta), -100) or not finite_number(comparison.get(budget)):
                    errors.append(f"comparison {delta}/{budget} must be finite")
                elif comparison[delta] > comparison[budget]:
                    errors.append(f"comparison.{delta} exceeds {budget}")
        if dataset.get("visibility") not in {"private", "sequestered"} or dataset.get("split") not in {"holdout", "adversarial"}:
            errors.append("promotion requires private/sequestered holdout or adversarial data")
        if dataset.get("contamination_checked") is not True or dataset.get("contamination_found") is not False:
            errors.append("promotion requires a clean contamination check")
        if len(scenario_ids) < 3 or behavior_trials < len(scenario_ids) * 3:
            errors.append("promotion requires at least 3 scenarios and 3 behavior trials per scenario")
        if actual["agent_failure"] or actual["infrastructure_error"]:
            errors.append("promotion sample cannot contain agent or infrastructure failures")
    elif decision == "promote":
        errors.append("ineligible evidence cannot be promoted")
    elif comparison is not None and decision == "report_only":
        errors.append("report_only evidence must not claim a release comparison")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        path = regular_input_file(args.path)
        if path is None: raise ValueError("path must be a regular file, not a symlink")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [f"cannot read valid JSON: {exc}"]
    else:
        errors = validate(data, Path.cwd())
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        print("skill eval run invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
    else:
        print("skill eval run valid")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
