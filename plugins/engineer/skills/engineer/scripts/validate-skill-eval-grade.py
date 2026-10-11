#!/usr/bin/env python3
"""Validate and canonically replay a deterministic skill-eval grade receipt."""

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


def load_grader() -> Any:
    path = Path(__file__).with_name("grade-skill-eval-capture.py")
    spec = importlib.util.spec_from_file_location("engineer_eval_grader", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load deterministic grader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(data: Any, root: Path) -> list[str]:
    if not isinstance(data, dict):
        return ["grade receipt root must be an object"]
    capture = safe_path(data.get("capture", {}).get("path") if isinstance(data.get("capture"), dict) else None, root)
    oracle = safe_path(data.get("oracle", {}).get("path") if isinstance(data.get("oracle"), dict) else None, root)
    if capture is None or oracle is None or not capture.is_file() or not oracle.is_file():
        return ["grade receipt capture or oracle path is unsafe or missing"]
    try:
        expected = load_grader().grade(capture, oracle, root)
    except (OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
        return [f"canonical replay failed: {exc}"]
    return [] if data == expected else ["grade receipt differs from canonical deterministic replay"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        receipt = regular_input_file(args.receipt)
        if receipt is None: raise ValueError("receipt must be a regular file, not a symlink")
        data = json.loads(receipt.read_text(encoding="utf-8"))
        errors = validate(data, Path(args.root).resolve())
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors = [str(exc)]
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
    else:
        print("skill eval grade receipt valid")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
