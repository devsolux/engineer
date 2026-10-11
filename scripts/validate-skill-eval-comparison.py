#!/usr/bin/env python3
"""Validate and replay a paired skill-eval comparison report."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

sys.dont_write_bytecode = True


def load_comparator() -> Any:
    path = Path(__file__).with_name("compare-skill-eval-grades.py")
    spec = importlib.util.spec_from_file_location("engineer_eval_comparator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load comparison compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(data: Any, root: Path) -> list[str]:
    if not isinstance(data, dict):
        return ["comparison report root must be an object"]
    plan = safe_path(data.get("plan", {}).get("path") if isinstance(data.get("plan"), dict) else None, root)
    if plan is None or not plan.is_file():
        return ["comparison plan path is unsafe or missing"]
    try:
        expected = load_comparator().compile_report(plan, root)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        return [f"canonical replay failed: {exc}"]
    return [] if data == expected else ["comparison report differs from canonical deterministic replay"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = regular_input_file(args.report)
        if report is None: raise ValueError("report must be a regular file, not a symlink")
        data = json.loads(report.read_text(encoding="utf-8"))
        errors = validate(data, Path(args.root).resolve())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [str(exc)]
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print("skill eval comparison report valid")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
