#!/usr/bin/env python3
"""Validate engineer's local, content-free evaluation telemetry JSONL."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX = re.compile(r"^[0-9a-f]{64}$")
ROOT_KEYS = {"schema_version", "event_kind", "recorded_at", "event_id", "engineer", "host", "run", "quality", "privacy", "source"}
FORBIDDEN_KEYS = {"prompt", "response", "content", "code", "path", "url", "email", "user", "account", "session", "command", "tool_input", "tool_output"}


def forbidden(value: Any, location: str = "root") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered in FORBIDDEN_KEYS or lowered.endswith(("_prompt", "_response", "_path", "_url", "_email", "_account_uuid", "_tool_input", "_tool_output")):
                hits.append(f"{location}.{key}")
            hits.extend(forbidden(child, f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(forbidden(child, f"{location}[{index}]"))
    return hits


def validate(event: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(event, dict) or set(event) != ROOT_KEYS:
        return [f"root keys must be exactly {sorted(ROOT_KEYS)}"]
    kind = event.get("event_kind")
    if event.get("schema_version") != 2 or kind not in {"skill_eval_capture", "skill_eval_grade"}:
        errors.append("schema or event_kind invalid")
    if not isinstance(event.get("recorded_at"), str) or not event["recorded_at"].endswith("Z"):
        errors.append("recorded_at must be a UTC timestamp")
    if not HEX.fullmatch(str(event.get("event_id", ""))):
        errors.append("event_id must be a one-way SHA-256 identifier")

    engineer = event.get("engineer", {})
    if set(engineer) != {"version", "bundle_sha256"} or not isinstance(engineer.get("version"), str) or not HEX.fullmatch(str(engineer.get("bundle_sha256", ""))):
        errors.append("engineer binding invalid")
    host = event.get("host", {})
    if set(host) != {"name", "model"} or host.get("name") not in {"codex", "claude"} or not isinstance(host.get("model"), str) or len(host.get("model", "")) > 128:
        errors.append("host metadata invalid")
    run = event.get("run", {})
    if set(run) != {"scenario_id", "duration_ms", "exit_code", "timed_out"} or not isinstance(run.get("scenario_id"), int) or isinstance(run.get("scenario_id"), bool) or run.get("scenario_id", 0) < 1 or not isinstance(run.get("duration_ms"), int) or run.get("duration_ms", -1) < 0 or not isinstance(run.get("exit_code"), int) or type(run.get("timed_out")) is not bool:
        errors.append("run metrics invalid")
    quality = event.get("quality", {})
    expected_quality = {"capture_succeeded", "behavioral_pass", "grading_required", "error_class"} if kind == "skill_eval_capture" else {"capture_succeeded", "behavioral_pass", "grading_required", "error_class", "score", "safety_pass"}
    if set(quality) != expected_quality or type(quality.get("capture_succeeded")) is not bool or quality.get("behavioral_pass") not in {True, False, None} or type(quality.get("grading_required")) is not bool or quality.get("error_class") not in {"none", "agent_failure", "infrastructure_error", "ungraded"}:
        errors.append("quality classification invalid")
    if kind == "skill_eval_capture" and (quality.get("behavioral_pass") is not None or quality.get("grading_required") is not True or quality.get("error_class") not in {"ungraded", "infrastructure_error"}):
        errors.append("capture event must remain explicitly ungraded")
    if kind == "skill_eval_grade" and (type(quality.get("behavioral_pass")) is not bool or quality.get("grading_required") is not False or not isinstance(quality.get("score"), (int, float)) or isinstance(quality.get("score"), bool) or not 0 <= quality.get("score", -1) <= 1 or type(quality.get("safety_pass")) is not bool or quality.get("error_class") == "ungraded"):
        errors.append("grade event quality invalid")
    privacy = event.get("privacy", {})
    required_privacy = {"content_recorded": False, "paths_recorded": False, "identity_recorded": False, "export": "local_only"}
    if privacy != required_privacy:
        errors.append("privacy contract must remain metadata-only and local-only")
    source = event.get("source", {})
    if set(source) != {"artifact_sha256", "capture_sha256"} or not all(HEX.fullmatch(str(source.get(key, ""))) for key in source):
        errors.append("source capture binding invalid")
    hits = forbidden(event)
    if hits:
        errors.append(f"forbidden content or identity fields: {hits}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors: list[str] = []
    jsonl = regular_input_file(args.jsonl)
    try:
        if jsonl is None: raise ValueError("telemetry ledger must be a regular file, not a symlink")
        lines = jsonl.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError) as exc:
        lines = []
        errors.append(str(exc))
    if not lines:
        errors.append("telemetry ledger must contain at least one event")
    seen_ids: set[str] = set()
    seen_sources: set[tuple[str, str]] = set()
    for index, line in enumerate(lines, 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {index}: invalid JSON: {exc}")
            continue
        errors.extend(f"line {index}: {error}" for error in validate(event))
        event_id = event.get("event_id") if isinstance(event, dict) else None
        source = event.get("source", {}) if isinstance(event, dict) else {}
        source_key = (str(event.get("event_kind")), str(source.get("artifact_sha256"))) if isinstance(source, dict) else ("", "")
        if event_id in seen_ids:
            errors.append(f"line {index}: duplicate event_id")
        if source_key in seen_sources:
            errors.append(f"line {index}: duplicate event kind and source artifact")
        seen_ids.add(event_id)
        seen_sources.add(source_key)
    if args.json:
        print(json.dumps({"ok": not errors, "events": len(lines), "errors": errors}, indent=2))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}")
    else:
        print(f"engineer telemetry valid ({len(lines)} event(s))")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
