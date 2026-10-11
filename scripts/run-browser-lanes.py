#!/usr/bin/env python3
"""Compile and optionally execute a bounded multi-lane Playwright plan."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

LANES = {"public", "quality", "auth-read", "auth-write"}
READ_LANES = {"public", "quality", "auth-read"}
SAFE_ENV = {"PATH", "LANG", "LC_ALL", "CI"}
ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_relative(value: Any, root: Path, *, directory: bool = False) -> Path | None:
    path = safe_path(value, root)
    if path is None:
        return None
    if directory and not path.is_dir():
        return None
    return path


def canonical_origin(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname) and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and value == f"{parsed.scheme}://{parsed.netloc}"


def validate_plan(data: Any, root: Path) -> list[str]:
    errors: list[str] = []
    keys = {"schema_version", "run_kind", "run_id", "environment", "base_url", "app_root", "max_parallel", "lanes", "output_root"}
    if not isinstance(data, dict) or set(data) != keys or data.get("schema_version") != 1:
        return ["plan root or schema invalid"]
    if data.get("run_kind") not in {"illustrative_fixture", "captured_run"} or not ID.fullmatch(str(data.get("run_id", ""))):
        errors.append("run kind or ID invalid")
    if data.get("environment") not in {"preview", "staging"} or not canonical_origin(data.get("base_url")):
        errors.append("multi-lane execution requires a canonical preview or staging origin")
    if safe_relative(data.get("app_root"), root, directory=True) is None:
        errors.append("app_root must be an existing confined directory")
    output = safe_relative(data.get("output_root"), root)
    if output is None or output == root or not output.relative_to(root).as_posix().startswith(".engineer/browser-runs/"):
        errors.append("output_root must be confined beneath .engineer/browser-runs/")
    elif output.name != data.get("run_id"):
        errors.append("output_root final directory must equal run_id")
    app_root = safe_relative(data.get("app_root"), root, directory=True)
    if output is not None and app_root is not None and not output.is_relative_to(app_root):
        errors.append("output_root must be beneath app_root")
    if not isinstance(data.get("max_parallel"), int) or isinstance(data.get("max_parallel"), bool) or not 1 <= data.get("max_parallel", 0) <= 4:
        errors.append("max_parallel must be between 1 and 4")
    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        errors.append("lanes must be non-empty")
        return errors
    seen: set[str] = set()
    lane_keys = {"id", "kind", "workers", "timeout_seconds", "enabled"}
    for index, lane in enumerate(lanes):
        label = f"lane {index}"
        if not isinstance(lane, dict) or set(lane) != lane_keys:
            errors.append(f"{label} keys invalid")
            continue
        lane_id, kind = lane.get("id"), lane.get("kind")
        if not ID.fullmatch(str(lane_id or "")) or lane_id in seen:
            errors.append(f"{label} ID invalid or duplicate")
        else:
            seen.add(lane_id)
        if kind not in LANES or type(lane.get("enabled")) is not bool:
            errors.append(f"{label} kind or enabled invalid")
        if not isinstance(lane.get("workers"), int) or isinstance(lane.get("workers"), bool) or not 1 <= lane.get("workers", 0) <= 8:
            errors.append(f"{label} workers invalid")
        if kind == "auth-write" and lane.get("workers") != 1:
            errors.append(f"{label} auth-write must use one worker")
        if kind == "auth-read" and lane.get("workers") != 1:
            errors.append(f"{label} auth-read must use one worker until per-worker authentication is configured")
        if not isinstance(lane.get("timeout_seconds"), int) or isinstance(lane.get("timeout_seconds"), bool) or not 10 <= lane.get("timeout_seconds", 0) <= 1800:
            errors.append(f"{label} timeout invalid")
    if sum(lane.get("kind") == "auth-write" and lane.get("enabled") is True for lane in lanes if isinstance(lane, dict)) > 1:
        errors.append("only one shared auth-write lane is allowed")
    if not any(lane.get("enabled") is True for lane in lanes if isinstance(lane, dict)):
        errors.append("at least one lane must be enabled")
    return errors


def command_for(lane: dict[str, Any]) -> list[str]:
    return ["pnpm", "exec", "playwright", "test", "--reporter=json", f"--workers={lane['workers']}", "--max-failures=10"]


def public_commands(data: dict[str, Any]) -> list[dict[str, Any]]:
    commands = []
    for lane in data["lanes"]:
        if lane["enabled"]:
            commands.append({
                "lane_id": lane["id"], "kind": lane["kind"], "phase": "serial_write" if lane["kind"] == "auth-write" else "parallel_read",
                "argv": command_for(lane),
                "fixed_environment_names": ["BASE_URL", "E2E_LANE", "E2E_OUTPUT_DIR", "E2E_WORKERS", "HOME", "PLAYWRIGHT_JSON_OUTPUT_DIR", "PLAYWRIGHT_JSON_OUTPUT_NAME", "TMPDIR"],
                "inherited_environment_allowlist": sorted(SAFE_ENV),
                "credential_environment_names": ["E2E_EMAIL", "E2E_PASSWORD"] if lane["kind"] in {"auth-read", "auth-write"} else [],
            })
    return commands


def run_lane(data: dict[str, Any], lane: dict[str, Any], root: Path, app_root: Path, output_root: Path) -> dict[str, Any]:
    lane_root = output_root / lane["id"]
    lane_root.mkdir(parents=True, exist_ok=False)
    home, temp = lane_root / "home", lane_root / "tmp"
    home.mkdir(); temp.mkdir()
    relative_lane_root = lane_root.relative_to(app_root).as_posix()
    env = {key: value for key, value in os.environ.items() if key in SAFE_ENV}
    env.update({
        "BASE_URL": data["base_url"], "E2E_LANE": lane["kind"], "E2E_WORKERS": str(lane["workers"]),
        "E2E_OUTPUT_DIR": f"{relative_lane_root}/test-results", "PLAYWRIGHT_JSON_OUTPUT_DIR": relative_lane_root,
        "PLAYWRIGHT_JSON_OUTPUT_NAME": "results.json", "HOME": str(home), "TMPDIR": str(temp),
    })
    if lane["kind"] in {"auth-read", "auth-write"}:
        env.update({"E2E_EMAIL": os.environ["E2E_EMAIL"], "E2E_PASSWORD": os.environ["E2E_PASSWORD"]})
    argv = command_for(lane)
    stdout_path, stderr_path = lane_root / "stdout.log", lane_root / "stderr.log"
    started = now(); monotonic = time.monotonic(); timed_out = False
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        try:
            completed = subprocess.run(argv, cwd=app_root, env=env, stdout=stdout, stderr=stderr, timeout=lane["timeout_seconds"], check=False)
            exit_code = completed.returncode
        except subprocess.TimeoutExpired:
            timed_out, exit_code = True, 124
    ended = now()
    report = lane_root / "results.json"
    artifacts = []
    for kind, path in (("report", report), ("stdout", stdout_path), ("stderr", stderr_path)):
        if path.is_file():
            artifacts.append({"kind": kind, "path": path.relative_to(root).as_posix(), "sha256": digest(path), "bytes": path.stat().st_size})
    return {
        "id": lane["id"], "kind": lane["kind"], "phase": "serial_write" if lane["kind"] == "auth-write" else "parallel_read",
        "started_at": started, "ended_at": ended, "duration_ms": round((time.monotonic() - monotonic) * 1000),
        "exit_code": exit_code, "timed_out": timed_out, "command_sha256": hashlib.sha256(json.dumps(argv).encode()).hexdigest(),
        "report_present": report.is_file(), "artifacts": artifacts,
    }


def execute(data: dict[str, Any], plan_path: Path, root: Path) -> dict[str, Any]:
    app_root = safe_relative(data["app_root"], root, directory=True)
    output_root = safe_relative(data["output_root"], root)
    assert app_root is not None and output_root is not None
    if plan_path.is_relative_to(root) is False:
        raise ValueError("plan must be confined beneath root")
    if output_root.exists():
        raise ValueError("output_root already exists; run IDs and evidence directories are immutable")
    reads = [lane for lane in data["lanes"] if lane["enabled"] and lane["kind"] in READ_LANES]
    writes = [lane for lane in data["lanes"] if lane["enabled"] and lane["kind"] == "auth-write"]
    auth_state = app_root / "playwright" / ".auth" / "user.json"
    if (any(lane["kind"] in {"auth-read", "auth-write"} for lane in reads + writes) and auth_state.exists()):
        raise ValueError("refusing to reuse or overwrite an existing Playwright auth state")
    output_root.mkdir(parents=True)
    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=data["max_parallel"]) as pool:
            futures = [pool.submit(run_lane, data, lane, root, app_root, output_root) for lane in reads]
            for future in futures:
                results.append(future.result())
        for lane in writes:
            results.append(run_lane(data, lane, root, app_root, output_root))
    finally:
        auth_state.unlink(missing_ok=True)
    results.sort(key=lambda item: item["id"])
    success = all(item["exit_code"] == 0 and not item["timed_out"] and item["report_present"] for item in results)
    return {
        "schema_version": 1, "receipt_kind": "captured_run", "run_id": data["run_id"],
        "plan": {"path": plan_path.relative_to(root).as_posix(), "sha256": digest(plan_path)},
        "base_origin": data["base_url"], "environment": data["environment"], "max_parallel": data["max_parallel"],
        "lanes": results, "decision": {"outcome": "pass" if success else "fail", "receipt_compilation_required": True,
        "reason": "All selected Playwright lanes exited cleanly with JSON reports." if success else "One or more Playwright lanes failed, timed out, or omitted its JSON report."},
        "limitations": ["Runner evidence proves process scheduling and raw artifact binding, not browser-session policy compliance.", "Local command hashes do not attest the resolved pnpm, Playwright binary, runner, browser, or JSON-report semantics.", "Compile and independently review browser-session and aggregate lane receipts before promotion."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--print-commands", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--acknowledge-mutations", action="store_true")
    args = parser.parse_args()
    root, plan_path = args.root.resolve(), regular_input_file(args.plan)
    if plan_path is None:
        print("ERROR: plan must be a regular file, not a symlink", file=sys.stderr)
        return 2
    try:
        data = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    errors = validate_plan(data, root)
    if errors:
        for error in errors: print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.execute and data["run_kind"] != "captured_run":
        print("ERROR: illustrative plans cannot execute", file=sys.stderr); return 2
    has_write = any(lane["enabled"] and lane["kind"] == "auth-write" for lane in data["lanes"])
    if args.execute and has_write and not args.acknowledge_mutations:
        print("ERROR: auth-write execution requires --acknowledge-mutations", file=sys.stderr); return 2
    auth = any(lane["enabled"] and lane["kind"] in {"auth-read", "auth-write"} for lane in data["lanes"])
    if args.execute and auth and not all(os.environ.get(key) for key in ("E2E_EMAIL", "E2E_PASSWORD")):
        print("ERROR: authenticated lanes require E2E_EMAIL and E2E_PASSWORD", file=sys.stderr); return 2
    if not args.execute:
        print(json.dumps({"ok": True, "executable": False, "commands": public_commands(data)}, indent=2)); return 0
    try:
        receipt = execute(data, plan_path, root)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    output_root = safe_relative(data["output_root"], root)
    assert output_root is not None
    receipt_path = output_root / "execution.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": receipt["decision"]["outcome"] == "pass", "receipt": receipt_path.relative_to(root).as_posix()}, indent=2))
    return 0 if receipt["decision"]["outcome"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
