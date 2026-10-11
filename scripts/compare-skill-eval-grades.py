#!/usr/bin/env python3
"""Compile paired baseline/candidate grade receipts into a promotion report."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import create_new_text, regular_input_file, relative_posix, safe_path

sys.dont_write_bytecode = True


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_grade_validator() -> Any:
    path = Path(__file__).with_name("validate-skill-eval-grade.py")
    spec = importlib.util.spec_from_file_location("engineer_grade_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load grade validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wilson(passes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    p = passes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, center - margin), min(1.0, center + margin)]


def load_receipts(paths: list[str], root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    validator = load_grade_validator()
    receipts, bindings = [], []
    for value in paths:
        path = safe_path(value, root)
        if path is None or not path.is_file():
            raise ValueError(f"unsafe or missing grade receipt: {value}")
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validator.validate(data, root)
        if errors:
            raise ValueError(f"invalid grade receipt {value}: {'; '.join(errors)}")
        receipts.append(data)
        bindings.append({"path": value, "sha256": digest(path)})
    return receipts, bindings


def compile_report(plan_path: Path, root: Path) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    keys = {"schema_version", "comparison_id", "baseline", "candidate", "gates"}
    if not isinstance(plan, dict) or set(plan) != keys or plan.get("schema_version") != 1:
        raise ValueError("comparison plan root or schema invalid")
    if not isinstance(plan.get("comparison_id"), str) or not plan["comparison_id"]:
        raise ValueError("comparison_id must be non-empty")
    gates = plan.get("gates")
    gate_keys = {"min_scenarios", "min_trials_per_scenario", "max_pass_rate_drop", "max_safety_regressions"}
    if not isinstance(gates, dict) or set(gates) != gate_keys:
        raise ValueError("comparison gates invalid")
    if any(not isinstance(gates.get(key), int) or isinstance(gates.get(key), bool) or gates[key] < 0 for key in ("min_scenarios", "min_trials_per_scenario", "max_safety_regressions")) or not isinstance(gates.get("max_pass_rate_drop"), (int, float)) or isinstance(gates.get("max_pass_rate_drop"), bool) or gates["max_pass_rate_drop"] < 0:
        raise ValueError("comparison gate values invalid")
    for variant in ("baseline", "candidate"):
        if not isinstance(plan.get(variant), list) or not plan[variant] or len(plan[variant]) != len(set(plan[variant])):
            raise ValueError(f"{variant} receipt paths must be a non-empty unique list")
    baseline, baseline_bindings = load_receipts(plan["baseline"], root)
    candidate, candidate_bindings = load_receipts(plan["candidate"], root)

    def indexed(receipts: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
        result: dict[tuple[Any, ...], dict[str, Any]] = {}
        for receipt in receipts:
            pair_key = (receipt["host"], receipt["model"], receipt["scenario_id"], receipt["dataset"]["trial_id"])
            if pair_key in result:
                raise ValueError("duplicate host/model/scenario/trial identity")
            result[pair_key] = receipt
        return result

    left, right = indexed(baseline), indexed(candidate)
    if set(left) != set(right):
        raise ValueError("baseline and candidate do not have identical host/model/scenario trial coverage")
    pair_rows = []
    for pair_key in sorted(left):
        before, after = left[pair_key], right[pair_key]
        if before["dataset"]["seed"] != after["dataset"]["seed"]:
            raise ValueError("paired baseline and candidate seeds differ")
        pair_rows.append({
            "host": pair_key[0], "model": pair_key[1], "scenario_id": pair_key[2], "trial_id": pair_key[3], "seed": before["dataset"]["seed"],
            "baseline_pass": before["summary"]["behavioral_pass"], "candidate_pass": after["summary"]["behavioral_pass"],
            "baseline_safety_pass": before["summary"]["safety_pass"], "candidate_safety_pass": after["summary"]["safety_pass"],
        })
    b_pass = sum(row["baseline_pass"] for row in pair_rows)
    c_pass = sum(row["candidate_pass"] for row in pair_rows)
    total = len(pair_rows)
    regressions = sum(row["baseline_pass"] and not row["candidate_pass"] for row in pair_rows)
    safety_regressions = sum(row["baseline_safety_pass"] and not row["candidate_safety_pass"] for row in pair_rows)
    scenario_counts = Counter(row["scenario_id"] for row in pair_rows)
    all_receipts = baseline + candidate
    baseline_versions = {r["skill_sha256"] for r in baseline}
    candidate_versions = {r["skill_sha256"] for r in candidate}
    paired_versions = len(baseline_versions) == 1 and len(candidate_versions) == 1 and baseline_versions != candidate_versions
    captured = all(r["grade_kind"] == "captured_run" for r in all_receipts)
    private_holdout = all(r["dataset"]["split"] == "holdout" and r["dataset"]["visibility"] in {"private", "sequestered"} for r in all_receipts)
    pass_drop = b_pass / total - c_pass / total
    gate_results = {
        "distinct_variants": paired_versions,
        "captured_evidence": captured,
        "private_holdout": private_holdout,
        "scenario_count": len(scenario_counts) >= gates["min_scenarios"],
        "trials_per_scenario": min(scenario_counts.values()) >= gates["min_trials_per_scenario"],
        "pass_rate": pass_drop <= gates["max_pass_rate_drop"],
        "safety": safety_regressions <= gates["max_safety_regressions"],
    }
    eligible = all(gate_results.values())
    return {
        "schema_version": 1,
        "comparison_kind": "captured_run" if captured else "illustrative_fixture",
        "comparison_id": plan["comparison_id"],
        "plan": {"path": relative_posix(plan_path, root), "sha256": digest(plan_path)},
        "bindings": {"baseline": baseline_bindings, "candidate": candidate_bindings},
        "coverage": {"pairs": total, "scenarios": sorted(scenario_counts), "trials_per_scenario": {str(k): scenario_counts[k] for k in sorted(scenario_counts)}},
        "metrics": {
            "baseline_pass_rate": b_pass / total, "candidate_pass_rate": c_pass / total,
            "pass_rate_delta": c_pass / total - b_pass / total,
            "baseline_pass_rate_ci95": wilson(b_pass, total), "candidate_pass_rate_ci95": wilson(c_pass, total),
            "per_trial_regressions": regressions, "safety_regressions": safety_regressions,
        },
        "pairs": pair_rows,
        "gate_results": gate_results,
        "promotion": {"eligible": eligible, "decision": "promote" if eligible else "report_only", "reason": "All deterministic paired promotion gates pass." if eligible else "One or more deterministic paired promotion gates failed."},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        plan = regular_input_file(args.plan)
        if plan is None:
            raise ValueError("plan must be a regular file, not a symlink")
        report = compile_report(plan, root)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        try:
            create_new_text(args.output, rendered)
        except (OSError, ValueError) as exc:
            print(f"ERROR: cannot publish comparison: {exc}", file=sys.stderr)
            return 1
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
