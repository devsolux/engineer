#!/usr/bin/env python3
"""Validate a raw multi-lane Playwright execution receipt and its artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

sys.dont_write_bytecode = True
LIMITATIONS = ["Runner evidence proves process scheduling and raw artifact binding, not browser-session policy compliance.", "Local command hashes do not attest the resolved pnpm, Playwright binary, runner, browser, or JSON-report semantics.", "Compile and independently review browser-session and aggregate lane receipts before promotion."]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
    except ValueError:
        return None


def load_runner() -> Any:
    path = Path(__file__).with_name("run-browser-lanes.py")
    spec = importlib.util.spec_from_file_location("engineer_browser_lane_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load lane runner")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def validate(data: Any, root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []; gates: list[str] = []
    keys = {"schema_version", "receipt_kind", "run_id", "plan", "base_origin", "environment", "max_parallel", "lanes", "decision", "limitations"}
    if not isinstance(data, dict) or set(data) != keys or data.get("schema_version") != 1 or data.get("receipt_kind") != "captured_run":
        return ["execution receipt root, schema, or kind invalid"], []
    plan_ref = data.get("plan", {})
    plan_path = safe_path(plan_ref.get("path") if isinstance(plan_ref, dict) else None, root)
    if not isinstance(plan_ref, dict) or set(plan_ref) != {"path", "sha256"} or plan_path is None or not plan_path.is_file() or digest(plan_path) != plan_ref.get("sha256"):
        return ["plan binding invalid"], []
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8")); runner = load_runner()
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        return [f"plan or runner load failed: {exc}"], []
    plan_errors = runner.validate_plan(plan, root)
    if plan_errors or plan.get("run_kind") != "captured_run":
        errors.append("bound plan is not a valid captured-run plan")
    if data.get("run_id") != plan.get("run_id") or data.get("base_origin") != plan.get("base_url") or data.get("environment") != plan.get("environment") or data.get("max_parallel") != plan.get("max_parallel"):
        gates.append("receipt identity or environment differs from plan")
    output_root = safe_path(plan.get("output_root"), root)
    lanes = data.get("lanes")
    if not isinstance(lanes, list):
        errors.append("lanes must be an array"); lanes = []
    enabled = {lane["id"]: lane for lane in plan.get("lanes", []) if isinstance(lane, dict) and lane.get("enabled") is True}
    observed_ids = {lane.get("id") for lane in lanes if isinstance(lane, dict)}
    if observed_ids != set(enabled) or len(observed_ids) != len(lanes):
        gates.append("execution lanes do not exactly cover enabled plan lanes")
    read_ends: list[datetime] = []; write_starts: list[datetime] = []; derived_success = True
    lane_keys = {"id", "kind", "phase", "started_at", "ended_at", "duration_ms", "exit_code", "timed_out", "command_sha256", "report_present", "artifacts"}
    for index, lane in enumerate(lanes):
        label = f"lane {index}"
        if not isinstance(lane, dict) or set(lane) != lane_keys or lane.get("id") not in enabled:
            errors.append(f"{label} shape or identity invalid"); continue
        declared = enabled[lane["id"]]
        expected_phase = "serial_write" if declared["kind"] == "auth-write" else "parallel_read"
        if lane.get("kind") != declared["kind"] or lane.get("phase") != expected_phase:
            gates.append(f"{label} kind or phase differs from plan")
        start, end = timestamp(lane.get("started_at")), timestamp(lane.get("ended_at"))
        if start is None or end is None or start >= end or not isinstance(lane.get("duration_ms"), int) or lane.get("duration_ms", -1) < 0:
            errors.append(f"{label} timing invalid")
        elif expected_phase == "serial_write": write_starts.append(start)
        else: read_ends.append(end)
        expected_command = hashlib.sha256(json.dumps(runner.command_for(declared)).encode()).hexdigest()
        if lane.get("command_sha256") != expected_command:
            gates.append(f"{label} command digest differs from canonical runner")
        if not isinstance(lane.get("exit_code"), int) or type(lane.get("timed_out")) is not bool or type(lane.get("report_present")) is not bool:
            errors.append(f"{label} execution result invalid")
        lane_success = lane.get("exit_code") == 0 and lane.get("timed_out") is False and lane.get("report_present") is True
        derived_success = derived_success and lane_success
        artifacts = lane.get("artifacts")
        seen_kinds: set[str] = set()
        if not isinstance(artifacts, list): artifacts = []; errors.append(f"{label} artifacts invalid")
        lane_root = output_root / lane["id"] if output_root is not None else None
        for artifact in artifacts:
            if not isinstance(artifact, dict) or set(artifact) != {"kind", "path", "sha256", "bytes"} or artifact.get("kind") not in {"report", "stdout", "stderr"} or artifact.get("kind") in seen_kinds:
                errors.append(f"{label} artifact invalid"); continue
            seen_kinds.add(artifact["kind"]); path = safe_path(artifact.get("path"), root)
            if path is None or not path.is_file() or lane_root is None or not path.is_relative_to(lane_root) or digest(path) != artifact.get("sha256") or path.stat().st_size != artifact.get("bytes") or path.stat().st_size > 50_000_000:
                gates.append(f"{label} artifact path, digest, size, or bound invalid")
        required = {"stdout", "stderr", "report"} if lane.get("report_present") else {"stdout", "stderr"}
        if seen_kinds != required:
            gates.append(f"{label} required artifact set incomplete")
    if read_ends and write_starts and min(write_starts) < max(read_ends):
        gates.append("auth-write started before every parallel read lane ended")
    decision = data.get("decision", {})
    if not isinstance(decision, dict) or set(decision) != {"outcome", "receipt_compilation_required", "reason"} or decision.get("outcome") != ("pass" if derived_success else "fail") or decision.get("receipt_compilation_required") is not True or not isinstance(decision.get("reason"), str) or not decision.get("reason"):
        gates.append("decision is not derived or preserves no receipt-compilation boundary")
    if data.get("limitations") != LIMITATIONS:
        gates.append("mandatory execution-evidence limitations missing or altered")
    return errors, gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("receipt", type=Path); parser.add_argument("--root", type=Path, default=Path(".")); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    receipt = regular_input_file(args.receipt)
    if receipt is None:
        errors, gates = ["receipt must be a regular file, not a symlink"], []
    else:
        try: data = json.loads(receipt.read_text(encoding="utf-8")); errors, gates = validate(data, args.root.resolve())
        except (OSError, json.JSONDecodeError) as exc: errors, gates = [str(exc)], []
    if args.json: print(json.dumps({"valid": not errors and not gates, "errors": errors, "gates": gates}, indent=2))
    elif errors or gates:
        for item in errors: print(f"ERROR: {item}", file=sys.stderr)
        for item in gates: print(f"GATE: {item}", file=sys.stderr)
    else: print("browser lane execution valid")
    return 0 if not errors and not gates else 1


if __name__ == "__main__": raise SystemExit(main())
