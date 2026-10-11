#!/usr/bin/env python3
"""Summarize a valid local engineer telemetry ledger without exporting it."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jsonl", type=Path)
    args = parser.parse_args()
    jsonl = regular_input_file(args.jsonl)
    if jsonl is None:
        print("telemetry ledger must be a regular file, not a symlink", file=sys.stderr)
        return 2
    validator = Path(__file__).with_name("validate-engineer-telemetry.py")
    if subprocess.run([sys.executable, str(validator), str(jsonl)], capture_output=True).returncode != 0:
        print("telemetry ledger invalid", file=sys.stderr)
        return 2
    events = [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines()]
    captures = [event for event in events if event["event_kind"] == "skill_eval_capture"]
    graded = [event for event in events if event["event_kind"] == "skill_eval_grade"]
    durations = [event["run"]["duration_ms"] for event in graded or captures]
    graded_capture_hashes = {event["source"]["capture_sha256"] for event in graded}
    capture_hashes = {event["source"]["capture_sha256"] for event in captures}
    summary = {
        "schema_version": 2,
        "events": len(events),
        "event_kinds": dict(sorted(Counter(event["event_kind"] for event in events).items())),
        "hosts": dict(sorted(Counter(event["host"]["name"] for event in events).items())),
        "capture_success_rate": None if not captures else sum(event["quality"]["capture_succeeded"] for event in captures) / len(captures),
        "graded_events": len(graded),
        "behavioral_pass_rate": None if not graded else sum(event["quality"]["behavioral_pass"] for event in graded) / len(graded),
        "safety_failures": sum(not event["quality"]["safety_pass"] for event in graded),
        "ungraded_capture_backlog": len(capture_hashes - graded_capture_hashes),
        "error_classes": dict(sorted(Counter(event["quality"]["error_class"] for event in graded or captures).items())),
        "duration_ms": {"median": round(statistics.median(durations)), "max": max(durations)},
        "decision_note": "Use with outcome and trajectory graders; usage or speed alone does not measure engineer quality.",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
