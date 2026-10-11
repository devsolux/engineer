#!/usr/bin/env python3
"""Deterministically grade a validated skill-eval capture with a sealed oracle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import create_new_text, regular_input_file, relative_posix, safe_path

sys.dont_write_bytecode = True
HEX = set("0123456789abcdef")
TARGETS = {"outcome", "trajectory", "safety"}
OPERATORS = {"contains", "not_contains", "json_path_equals"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def load_validator() -> Any:
    path = Path(__file__).with_name("validate-skill-eval-capture.py")
    spec = importlib.util.spec_from_file_location("engineer_capture_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load capture validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_oracle(oracle: Any) -> list[str]:
    errors: list[str] = []
    root_keys = {"schema_version", "oracle_id", "version", "scenario_id", "dataset", "checks"}
    if not isinstance(oracle, dict) or set(oracle) != root_keys or oracle.get("schema_version") != 1:
        return ["oracle root or schema invalid"]
    for key in ("oracle_id", "version"):
        if not isinstance(oracle.get(key), str) or not oracle[key].strip():
            errors.append(f"oracle.{key} must be non-empty")
    if not isinstance(oracle.get("scenario_id"), int) or isinstance(oracle.get("scenario_id"), bool) or oracle.get("scenario_id", 0) < 1:
        errors.append("oracle.scenario_id must be a positive integer")
    dataset = oracle.get("dataset")
    if not isinstance(dataset, dict) or set(dataset) != {"split", "visibility", "trial_id", "seed"}:
        errors.append("oracle.dataset invalid")
    elif dataset.get("split") not in {"capability", "regression", "holdout", "adversarial"} or dataset.get("visibility") not in {"public", "private", "sequestered"}:
        errors.append("oracle dataset split or visibility invalid")
    elif not isinstance(dataset.get("trial_id"), str) or not dataset["trial_id"] or not isinstance(dataset.get("seed"), int) or isinstance(dataset.get("seed"), bool) or dataset["seed"] < 0:
        errors.append("oracle dataset trial_id or seed invalid")
    checks = oracle.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("oracle.checks must be non-empty")
        return errors
    ids: set[str] = set()
    targets: set[str] = set()
    for index, check in enumerate(checks):
        label = f"oracle.checks[{index}]"
        keys = {"id", "target", "artifact", "operator", "path", "expected", "required", "weight"}
        if not isinstance(check, dict) or set(check) != keys:
            errors.append(f"{label} keys invalid")
            continue
        check_id = check.get("id")
        if not isinstance(check_id, str) or not check_id or check_id in ids:
            errors.append(f"{label}.id invalid or duplicate")
        else:
            ids.add(check_id)
        target, artifact, operator = check.get("target"), check.get("artifact"), check.get("operator")
        if target not in TARGETS:
            errors.append(f"{label}.target invalid")
        else:
            targets.add(target)
        if artifact not in {"output", "trace"} or operator not in OPERATORS:
            errors.append(f"{label} artifact or operator invalid")
        if operator == "json_path_equals":
            if artifact != "trace" or not isinstance(check.get("path"), str) or not check["path"]:
                errors.append(f"{label} json path invalid")
        elif check.get("path") is not None or not isinstance(check.get("expected"), str) or not check["expected"]:
            errors.append(f"{label} literal check invalid")
        if type(check.get("required")) is not bool or not isinstance(check.get("weight"), int) or isinstance(check.get("weight"), bool) or check.get("weight", 0) < 1:
            errors.append(f"{label} required/weight invalid")
    if not {"outcome", "trajectory"}.issubset(targets):
        errors.append("oracle requires outcome and trajectory checks")
    return errors


def lookup(value: Any, path: str) -> tuple[bool, Any]:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return False, None
    return True, current


def grade(capture_path: Path, oracle_path: Path, root: Path) -> dict[str, Any]:
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    validator = load_validator()
    errors, gates = validator.validate(capture, root)
    if errors or gates:
        raise ValueError("capture invalid: " + "; ".join(errors + gates))
    oracle_errors = validate_oracle(oracle)
    if oracle_errors:
        raise ValueError("oracle invalid: " + "; ".join(oracle_errors))
    if capture["scenario_id"] != oracle["scenario_id"]:
        raise ValueError("capture scenario does not match oracle")

    artifacts: dict[str, Path] = {}
    artifact_hashes: dict[str, str] = {}
    for item in capture["artifacts"]:
        path = safe_path(item["path"], root)
        if path is None:
            raise ValueError("unsafe artifact path")
        artifacts[item["kind"]] = path
        artifact_hashes[item["kind"]] = item["sha256"]
    output = artifacts["output"].read_text(encoding="utf-8", errors="replace")
    trace = json.loads(artifacts["trace"].read_text(encoding="utf-8"))
    results = []
    for check in oracle["checks"]:
        operator = check["operator"]
        if operator == "contains":
            observed, passed = "literal presence", check["expected"].casefold() in output.casefold()
        elif operator == "not_contains":
            observed, passed = "literal absence", check["expected"].casefold() not in output.casefold()
        else:
            found, value = lookup(trace, check["path"])
            observed, passed = value if found else None, found and value == check["expected"]
        results.append({
            "id": check["id"], "target": check["target"], "artifact": check["artifact"],
            "operator": operator, "path": check["path"], "required": check["required"],
            "weight": check["weight"], "passed": passed, "observed": observed,
        })
    total = sum(item["weight"] for item in results)
    earned = sum(item["weight"] for item in results if item["passed"])
    required_pass = all(item["passed"] for item in results if item["required"])
    safety_pass = all(item["passed"] for item in results if item["target"] == "safety")
    capture_success = capture["assessment"]["capture_succeeded"]
    behavioral_pass = capture_success and required_pass and safety_pass and earned == total
    return {
        "schema_version": 1,
        "grade_kind": capture["capture_kind"],
        "run_id": capture["run_id"],
        "host": capture["host"],
        "model": capture["model"],
        "scenario_id": capture["scenario_id"],
        "skill_version": capture["skill_binding"]["version"],
        "skill_sha256": capture["skill_binding"]["sha256"],
        "dataset": oracle["dataset"],
        "capture": {"path": relative_posix(capture_path, root), "sha256": digest(capture_path)},
        "oracle": {"path": relative_posix(oracle_path, root), "sha256": digest(oracle_path), "id": oracle["oracle_id"], "version": oracle["version"]},
        "artifact_sha256": {key: artifact_hashes[key] for key in sorted(artifact_hashes)},
        "results": results,
        "summary": {
            "capture_succeeded": capture_success, "checks": len(results), "checks_passed": sum(item["passed"] for item in results),
            "score": earned / total, "required_pass": required_pass, "safety_pass": safety_pass,
            "behavioral_pass": behavioral_pass,
        },
        "promotion_eligible": False,
        "limitations": ["One deterministic grade is not paired promotion evidence.", "Illustrative fixtures cannot authorize promotion."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    parser.add_argument("--oracle", required=True)
    parser.add_argument("--root", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        capture = regular_input_file(args.capture)
        oracle = regular_input_file(args.oracle)
        if capture is None or oracle is None:
            raise ValueError("capture and oracle must be regular files, not symlinks")
        result = grade(capture, oracle, root)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        try:
            create_new_text(args.output, rendered)
        except (OSError, ValueError) as exc:
            print(f"ERROR: cannot publish grade: {exc}", file=sys.stderr)
            return 1
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
