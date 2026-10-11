#!/usr/bin/env python3
"""Validate engineer's agentic execution contract using the Python standard library."""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

ID = re.compile(r"^[a-z][a-z0-9_]*$")
PHASES = ["sense", "plan", "act", "observe", "critique", "checkpoint", "stop_or_continue"]
TOOL_CLASSES = {"read", "local_mutation", "external_reversible", "external_irreversible"}
REQUIRED_STOPS = {"all_acceptance_has_evidence", "verification_commands_pass", "evidence_artifact_written"}


def validate(data):
    errors = []
    def err(path, message): errors.append(f"{path}: {message}")
    if not isinstance(data, dict): return ["$: must be an object"]
    if data.get("schema_version") != 1: err("$.schema_version", "must equal 1")
    goal = data.get("goal")
    if not isinstance(goal, dict): err("$.goal", "must be an object")
    else:
        for key in ("outcome", "scope", "non_goals", "evidence"):
            if not goal.get(key): err(f"$.goal.{key}", "must not be empty")

    maps = {}
    for collection in ("requirements", "acceptance", "plan"):
        items = data.get(collection)
        maps[collection] = {}
        if not isinstance(items, list) or not items:
            err(f"$.{collection}", "must be a non-empty array"); continue
        for i, item in enumerate(items):
            path = f"$.{collection}[{i}]"
            if not isinstance(item, dict): err(path, "must be an object"); continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not ID.fullmatch(item_id): err(f"{path}.id", "invalid id"); continue
            if item_id in maps[collection]: err(f"{path}.id", "duplicate id")
            maps[collection][item_id] = item

    covered_req, covered_ac = set(), set()
    for i, item in enumerate(data.get("acceptance", []) if isinstance(data.get("acceptance"), list) else []):
        if not isinstance(item, dict): continue
        refs = item.get("requirement_ids")
        if not isinstance(refs, list) or not refs: err(f"$.acceptance[{i}].requirement_ids", "must not be empty"); refs = []
        for ref in refs:
            if ref not in maps["requirements"]: err(f"$.acceptance[{i}].requirement_ids", f"unknown {ref!r}")
            else: covered_req.add(ref)
        if not item.get("criterion") or not item.get("evidence"): err(f"$.acceptance[{i}]", "criterion and evidence are required")
        oracles = item.get("oracles")
        if not isinstance(oracles, list) or not oracles: err(f"$.acceptance[{i}].oracles", "must be a non-empty array")
        else:
            for j, oracle in enumerate(oracles):
                opath = f"$.acceptance[{i}].oracles[{j}]"
                if not isinstance(oracle, dict) or set(oracle) != {"artifact", "pointer", "operator", "expected"}: err(opath, "shape invalid"); continue
                artifact = oracle.get("artifact")
                if not isinstance(artifact, str) or not artifact or artifact.startswith("/") or ".." in artifact.split("/"): err(f"{opath}.artifact", "must be a confined relative path")
                elif not any(isinstance(ev, str) and (ev == artifact or ev.endswith("/" + artifact)) for ev in item.get("evidence", [])): err(f"{opath}.artifact", "must be named by acceptance evidence")
                if not isinstance(oracle.get("pointer"), str) or not oracle["pointer"].startswith("/"): err(f"{opath}.pointer", "must be a JSON pointer")
                if oracle.get("operator") not in {"eq", "neq", "gte", "lte", "contains"}: err(f"{opath}.operator", "unsupported operator")
    for i, item in enumerate(data.get("plan", []) if isinstance(data.get("plan"), list) else []):
        if not isinstance(item, dict): continue
        for field, target, covered in (("requirement_ids", "requirements", covered_req), ("acceptance_ids", "acceptance", covered_ac)):
            refs = item.get(field)
            if not isinstance(refs, list) or not refs: err(f"$.plan[{i}].{field}", "must not be empty"); continue
            for ref in refs:
                if ref not in maps[target]: err(f"$.plan[{i}].{field}", f"unknown {ref!r}")
                else: covered.add(ref)
        if not item.get("action") or not item.get("verify"): err(f"$.plan[{i}]", "action and verify are required")
    missing_req = set(maps["requirements"]) - covered_req
    missing_ac = set(maps["acceptance"]) - covered_ac
    if missing_req: err("$.requirements", f"uncovered requirements: {sorted(missing_req)}")
    if missing_ac: err("$.acceptance", f"unplanned acceptance: {sorted(missing_ac)}")

    loop = data.get("loop")
    if not isinstance(loop, dict): err("$.loop", "must be an object")
    else:
        if loop.get("phases") != PHASES: err("$.loop.phases", f"must equal {PHASES}")
        for key in ("max_steps", "max_retries_per_failure", "no_progress_limit"):
            if not isinstance(loop.get(key), int) or not 0 < loop[key] <= 1000: err(f"$.loop.{key}", "must be an integer from 1 to 1000")
        if not loop.get("checkpoint_path"): err("$.loop.checkpoint_path", "is required")

    tools = data.get("tools")
    if not isinstance(tools, list) or not tools: err("$.tools", "must be a non-empty array")
    else:
        names = set()
        for i, tool in enumerate(tools):
            path = f"$.tools[{i}]"
            if not isinstance(tool, dict): err(path, "must be an object"); continue
            if not tool.get("name") or tool["name"] in names: err(f"{path}.name", "must be present and unique")
            names.add(tool.get("name"))
            tool_class = tool.get("class")
            if tool_class not in TOOL_CLASSES: err(f"{path}.class", "invalid class")
            for key in ("approval", "idempotency", "output_trust"):
                if not tool.get(key): err(f"{path}.{key}", "is required")
            if tool.get("network") not in {"deny", "allowlist", "unrestricted"}: err(f"{path}.network", "must be deny, allowlist, or unrestricted")
            if not isinstance(tool.get("data_access"), list): err(f"{path}.data_access", "must be an array")
            if not isinstance(tool.get("allowed_sinks"), list): err(f"{path}.allowed_sinks", "must be an array")
            if not isinstance(tool.get("timeout_seconds"), int) or tool["timeout_seconds"] < 1: err(f"{path}.timeout_seconds", "must be positive")
            if tool_class != "read" and tool.get("approval") == "none": err(f"{path}.approval", "mutating tools need an approval policy")
            if isinstance(tool_class, str) and tool_class.startswith("external_") and not tool.get("allowed_sinks"): err(f"{path}.allowed_sinks", "external tools must declare destination sinks")
            if "network" in (tool.get("allowed_sinks") or []) and tool.get("network") == "deny": err(f"{path}.network", "cannot deny network while declaring a network sink")

    security = data.get("security")
    if not isinstance(security, dict): err("$.security", "must be an object")
    else:
        for key in ("untrusted_sources", "sensitive_data", "allowed_sinks"):
            if not isinstance(security.get(key), list) or not security[key]: err(f"$.security.{key}", "must be a non-empty array")
        if security.get("cross_domain_confirmation") is not True: err("$.security.cross_domain_confirmation", "must be true")
        if not security.get("injection_eval_set"): err("$.security.injection_eval_set", "is required")
        global_sinks = set(security.get("allowed_sinks", [])) if isinstance(security.get("allowed_sinks"), list) else set()
        for index, tool in enumerate(tools if isinstance(tools, list) else []):
            if isinstance(tool, dict) and isinstance(tool.get("allowed_sinks"), list):
                undeclared = set(tool["allowed_sinks"]) - global_sinks
                if undeclared: err(f"$.tools[{index}].allowed_sinks", f"not allowed by security policy: {sorted(undeclared)}")

    optimization = data.get("prompt_optimization")
    if not isinstance(optimization, dict): err("$.prompt_optimization", "must be an object")
    else:
        for key in ("baseline", "capability_set", "regression_set", "holdout_set", "quality_metric", "cost_budget", "latency_budget"):
            if not optimization.get(key): err(f"$.prompt_optimization.{key}", "is required")
        sets = [optimization.get(x) for x in ("capability_set", "regression_set", "holdout_set")]
        if len(set(sets)) != 3: err("$.prompt_optimization", "capability, regression, and holdout sets must differ")

    stops = data.get("stop_conditions")
    if not isinstance(stops, list): err("$.stop_conditions", "must be an array")
    else:
        missing = REQUIRED_STOPS - set(stops)
        if missing: err("$.stop_conditions", f"missing completion gates: {sorted(missing)}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        path = regular_input_file(args.file)
        if path is None: raise ValueError("file must be a regular file, not a symlink")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc: errors = [f"$: invalid JSON: {exc}"]
    else: errors = validate(data)
    if args.json: print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        print("agentic contract invalid", file=sys.stderr)
        for error in errors: print(f"- {error}", file=sys.stderr)
    else: print(f"agentic contract valid: {args.file}")
    return bool(errors)


if __name__ == "__main__": raise SystemExit(main())
