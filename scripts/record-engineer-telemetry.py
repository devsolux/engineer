#!/usr/bin/env python3
"""Append metadata-only local telemetry derived from a valid capture or grade."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_with(script: str, artifact: Path, root: Path) -> bool:
    validator = Path(__file__).with_name(script)
    checked = subprocess.run([sys.executable, str(validator), str(artifact), "--root", str(root)], capture_output=True, text=True)
    return checked.returncode == 0


def validate_ledger(path: Path) -> bool:
    validator = Path(__file__).with_name("validate-engineer-telemetry.py")
    return subprocess.run([sys.executable, str(validator), str(path)], capture_output=True).returncode == 0


def open_flags(base: int) -> int:
    return base | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)


def append_event(output: Path, event: dict[str, object]) -> int:
    """Serialize one validated ledger append under a sibling advisory lock."""
    lock_path = output.with_name(f"{output.name}.lock")
    lock_fd = os.open(lock_path, open_flags(os.O_RDWR | os.O_CREAT), 0o600)
    with os.fdopen(lock_fd, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        supplied_exists = output.exists() or output.is_symlink()
        if supplied_exists:
            current = regular_input_file(output)
            if current is None or current != output.resolve() or not validate_ledger(current):
                raise ValueError("existing telemetry ledger must be a valid regular file, not a symlink")
            before = os.stat(output, follow_symlinks=False)
            existing_ids = {
                json.loads(line).get("event_id")
                for line in current.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            if event["event_id"] in existing_ids:
                return 0
            descriptor = os.open(output, open_flags(os.O_WRONLY | os.O_APPEND))
            created = False
        else:
            descriptor = os.open(output, open_flags(os.O_WRONLY | os.O_CREAT | os.O_EXCL), 0o600)
            before = os.fstat(descriptor)
            created = True
        try:
            opened = os.fstat(descriptor)
            named = os.stat(output, follow_symlinks=False)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
                raise ValueError("telemetry ledger identity changed while locked")
            prior_size = opened.st_size
            line = (json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()
            view = memoryview(line)
            while view:
                view = view[os.write(descriptor, view):]
            os.fsync(descriptor)
            if not validate_ledger(output):
                os.ftruncate(descriptor, prior_size)
                os.fsync(descriptor)
                if created and prior_size == 0:
                    os.close(descriptor)
                    descriptor = -1
                    os.unlink(output)
                raise ValueError("telemetry ledger failed validation after append")
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    return 0


def base_event(event_kind: str, source_sha: str, version: str, bundle_sha: str, host: str, model: str, run: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 2,
        "event_kind": event_kind,
        "recorded_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "event_id": hashlib.sha256(f"{source_sha}:engineer-telemetry-v2:{event_kind}".encode()).hexdigest(),
        "engineer": {"version": version, "bundle_sha256": bundle_sha},
        "host": {"name": host, "model": model},
        "run": run,
        "privacy": {"content_recorded": False, "paths_recorded": False, "identity_recorded": False, "export": "local_only"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=Path(".engineer/telemetry/events.jsonl"))
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        artifact_path = regular_input_file(args.artifact)
        if artifact_path is None: raise ValueError("artifact must be a regular file, not a symlink")
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"invalid telemetry source: {exc}", file=sys.stderr)
        return 2
    artifact_sha = digest(artifact_path)
    if artifact.get("schema_version") == 5 and "assessment" in artifact:
        if not validate_with("validate-skill-eval-capture.py", artifact_path, root):
            print("capture must pass canonical validation before telemetry derivation", file=sys.stderr)
            return 2
        capture = artifact
        assessment = capture["assessment"]
        error_class = "infrastructure_error" if not assessment["capture_succeeded"] else "ungraded"
        event = base_event(
            "skill_eval_capture", artifact_sha, capture["skill_binding"]["version"], capture["skill_binding"]["sha256"], capture["host"], capture["model"],
            {"scenario_id": capture["scenario_id"], "duration_ms": capture["execution"]["duration_ms"], "exit_code": capture["execution"]["exit_code"], "timed_out": capture["execution"]["timed_out"]},
        )
        event["quality"] = {"capture_succeeded": assessment["capture_succeeded"], "behavioral_pass": None, "grading_required": True, "error_class": error_class}
        event["source"] = {"artifact_sha256": artifact_sha, "capture_sha256": artifact_sha}
    elif artifact.get("schema_version") == 1 and "results" in artifact and "oracle" in artifact:
        if not validate_with("validate-skill-eval-grade.py", args.artifact, root):
            print("grade must pass canonical replay before telemetry derivation", file=sys.stderr)
            return 2
        capture_path = safe_path(artifact["capture"]["path"], root)
        if capture_path is None or not capture_path.is_file():
            print("grade capture binding is unsafe or missing", file=sys.stderr)
            return 2
        capture = json.loads(capture_path.read_text(encoding="utf-8"))
        summary = artifact["summary"]
        error_class = "none" if summary["behavioral_pass"] else ("infrastructure_error" if not summary["capture_succeeded"] else "agent_failure")
        event = base_event(
            "skill_eval_grade", artifact_sha, artifact["skill_version"], artifact["skill_sha256"], artifact["host"], artifact["model"],
            {"scenario_id": artifact["scenario_id"], "duration_ms": capture["execution"]["duration_ms"], "exit_code": capture["execution"]["exit_code"], "timed_out": capture["execution"]["timed_out"]},
        )
        event["quality"] = {
            "capture_succeeded": summary["capture_succeeded"], "behavioral_pass": summary["behavioral_pass"], "grading_required": False,
            "error_class": error_class, "score": summary["score"], "safety_pass": summary["safety_pass"],
        }
        event["source"] = {"artifact_sha256": artifact_sha, "capture_sha256": artifact["capture"]["sha256"]}
    else:
        print("telemetry source must be a canonical capture or deterministic grade receipt", file=sys.stderr)
        return 2
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        return append_event(output, event)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"telemetry append rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
