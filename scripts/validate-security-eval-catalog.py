#!/usr/bin/env python3
"""Validate a safe, defensive engineer agent-security eval catalog."""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

REQUIRED_ATTACK_CATEGORIES = {
    "goal_hijack", "social_engineering", "tool_misuse", "identity_privilege",
    "supply_chain", "code_execution_sandbox", "memory_poisoning", "inter_agent_trust",
    "data_exfiltration", "network_ssrf", "persistence", "resource_exhaustion",
    "cascading_failure", "grader_oversight",
}
PAIRED_CATEGORIES = {"goal_hijack", "social_engineering", "memory_poisoning"}
SEVERITIES = {"low", "medium", "high", "critical"}
ID = re.compile(r"^[a-z][a-z0-9_]*$")
FORBIDDEN_KEYS = {"payload", "exploit_code", "live_credentials", "target_url", "shell_command"}
FORBIDDEN_CONTENT = re.compile(
    r"https?://|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|\bAKIA[0-9A-Z]{12,}|\bsk-[A-Za-z0-9]{12,}",
    re.IGNORECASE,
)


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    def err(path: str, message: str) -> None: errors.append(f"{path}: {message}")
    if not isinstance(data, dict): return ["$: must be an object"]
    if data.get("schema_version") != 1: err("$.schema_version", "must equal 1")
    if not isinstance(data.get("system"), str) or not data["system"].strip(): err("$.system", "is required")
    auth = data.get("authorization")
    if not isinstance(auth, dict): err("$.authorization", "must be an object")
    else:
        expected = {
            "authorized_only": True, "environment": "isolated_fixture", "live_targets": False,
            "synthetic_data": True, "destructive_actions_disabled": True,
        }
        for key, value in expected.items():
            if auth.get(key) != value: err(f"$.authorization.{key}", f"must equal {value!r}")
        if auth.get("network") not in {"deny", "simulated"}: err("$.authorization.network", "must be deny or simulated")
    prefix = data.get("canary_prefix")
    if not isinstance(prefix, str) or len(prefix) < 8: err("$.canary_prefix", "must be a distinctive inert prefix")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases: return errors + ["$.cases: must be a non-empty array"]
    by_id: dict[str, dict[str, Any]] = {}
    attack_categories: set[str] = set()
    regression_ids: set[str] = set()
    for index, case in enumerate(cases):
        path = f"$.cases[{index}]"
        if not isinstance(case, dict): err(path, "must be an object"); continue
        forbidden = FORBIDDEN_KEYS & set(case)
        if forbidden: err(path, f"must not contain operational attack fields: {sorted(forbidden)}")
        if FORBIDDEN_CONTENT.search(json.dumps(case)):
            err(path, "must not contain live URLs or credential-shaped material")
        case_id = case.get("id")
        if not isinstance(case_id, str) or ID.fullmatch(case_id) is None: err(f"{path}.id", "invalid id")
        elif case_id in by_id: err(f"{path}.id", "duplicate id")
        else: by_id[case_id] = case
        mode = case.get("mode")
        if mode not in {"attack", "benign"}: err(f"{path}.mode", "must be attack or benign")
        category = case.get("category")
        if not isinstance(category, str) or not category: err(f"{path}.category", "is required")
        elif mode == "attack": attack_categories.add(category)
        for field in ("title", "scenario", "fixture", "inert_canary", "owner", "regression_id"):
            if not isinstance(case.get(field), str) or not case[field].strip(): err(f"{path}.{field}", "must be a non-empty string")
        if isinstance(case.get("fixture"), str) and not case["fixture"].startswith("fixtures/"):
            err(f"{path}.fixture", "must reference an isolated fixtures/ path")
        canary = case.get("inert_canary")
        if isinstance(prefix, str) and isinstance(canary, str) and not canary.startswith(prefix): err(f"{path}.inert_canary", "must use the catalog canary prefix")
        for field in ("expected_safe_behavior", "forbidden_outcomes", "observable_signals", "cleanup"):
            value = case.get(field)
            if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value): err(f"{path}.{field}", "must be a non-empty string array")
        if case.get("severity") not in SEVERITIES: err(f"{path}.severity", f"must be one of {sorted(SEVERITIES)}")
        if mode == "attack" and case.get("severity") == "low": err(f"{path}.severity", "attack cases must be medium, high, or critical")
        regression = case.get("regression_id")
        if isinstance(regression, str):
            if regression in regression_ids: err(f"{path}.regression_id", "must be unique")
            regression_ids.add(regression)
    canaries = [case.get("inert_canary") for case in cases if isinstance(case, dict) and isinstance(case.get("inert_canary"), str)]
    if len(canaries) != len(set(canaries)): err("$.cases", "inert canaries must be unique")
    missing = REQUIRED_ATTACK_CATEGORIES - attack_categories
    if missing: err("$.cases", f"missing attack categories: {sorted(missing)}")
    for case_id, case in by_id.items():
        if case.get("mode") == "attack" and case.get("category") in PAIRED_CATEGORIES:
            benign_id = case.get("benign_case_id")
            benign = by_id.get(benign_id)
            if benign is None: err(f"$.cases[{case_id}].benign_case_id", "must reference a benign control")
            elif benign.get("mode") != "benign" or benign.get("category") != case.get("category"):
                err(f"$.cases[{case_id}].benign_case_id", "must reference a benign case in the same category")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        path = regular_input_file(args.file)
        if path is None: raise ValueError("file must be a regular file, not a symlink")
        errors = validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc: errors = [f"$: invalid JSON: {exc}"]
    if args.json: print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        print("security eval catalog invalid", file=sys.stderr)
        for error in errors: print(f"- {error}", file=sys.stderr)
    else: print(f"security eval catalog valid: {args.file}")
    return 1 if errors else 0


if __name__ == "__main__": raise SystemExit(main())
