#!/usr/bin/env python3
"""Offline trajectory path checker for agent skill fixtures.

Usage:
  python3 scripts/check-trajectory-fixture.py \\
    --fixture templates/fixtures/trajectory-fix-typecheck.json \\
    --trace path/to/recorded-steps.json

Fixture: templates/fixtures/*.json (see references/ai-evals.md)
Trace: JSON array of steps, or {"steps": [...]}

  [
    {"tool": "bash", "name": "typecheck", "ok": true, "exit": 0},
    {"tool": "edit", "name": "src/app.ts", "ok": true},
    {"tool": "bash", "name": "typecheck", "ok": true, "exit": 0}
  ]

Step id = "tool" or "tool:normalized_name" (typecheck aliases normalized).
Exit 0 on pass, 1 on fail. No model calls.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    n = str(name).lower().strip()
    compact = n.replace(" ", "")
    if "typecheck" in n or "tsc--noemit" in compact or compact.endswith("tsc"):
        return "typecheck"
    return str(name)


def step_id(step: dict) -> str:
    tool = str(step.get("tool") or step.get("type") or "unknown")
    name = normalize_name(
        step.get("name") or step.get("command") or step.get("id")
    )
    return f"{tool}:{name}" if name else tool


def normalize_steps(raw: Any) -> list[dict]:
    if isinstance(raw, list):
        return [s for s in raw if isinstance(s, dict)]
    if isinstance(raw, dict):
        steps = raw.get("steps") or raw.get("trace") or []
        return [s for s in steps if isinstance(s, dict)]
    return []


def step_matches(item: str, need: str) -> bool:
    if item == need:
        return True
    # fixture "edit" matches recorded "edit:path/file.ts"
    if ":" not in need and item.startswith(need + ":"):
        return True
    return False


def has_subsequence(seq: list[str], sub: list[str]) -> bool:
    if not sub:
        return True
    i = 0
    for item in seq:
        if step_matches(item, sub[i]):
            i += 1
            if i == len(sub):
                return True
    return False


def final_typecheck_ok(steps: list[dict]) -> bool | None:
    for s in reversed(steps):
        if "typecheck" not in step_id(s):
            continue
        if s.get("ok") is True:
            return True
        if s.get("ok") is False:
            return False
        exit_code = s.get("exit")
        if exit_code in (0, "0"):
            return True
        if exit_code is not None:
            return False
        return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", required=True, type=Path)
    ap.add_argument("--trace", required=True, type=Path)
    args = ap.parse_args()

    fixture = regular_input_file(args.fixture)
    trace = regular_input_file(args.trace)
    if fixture is None or trace is None:
        print("fixture and trace must be regular files, not symlinks", file=sys.stderr)
        return 2
    fix = load_json(fixture)
    steps = normalize_steps(load_json(trace))
    errors: list[str] = []

    allowed = set(fix.get("allowed_tools") or [])
    forbidden = set(fix.get("forbidden_tools") or [])
    max_steps = int(fix.get("max_steps") or 0)
    subseq = list(fix.get("must_include_subsequence") or [])

    ids = [step_id(s) for s in steps]
    tools = [str(s.get("tool") or s.get("type") or "unknown") for s in steps]

    if max_steps and len(steps) > max_steps:
        errors.append(f"max_steps exceeded: {len(steps)} > {max_steps}")

    for t in tools:
        if t in forbidden:
            errors.append(f"forbidden tool used: {t}")
        if allowed and t not in allowed:
            errors.append(f"tool not in allowed_tools: {t}")

    if subseq and not has_subsequence(ids, subseq):
        errors.append(f"missing subsequence {subseq}; got {ids}")

    pass_if = str(fix.get("pass_if") or "")
    if "typecheck exit 0" in pass_if:
        ok = final_typecheck_ok(steps)
        if ok is not True:
            errors.append(f"pass_if failed: final typecheck not ok ({ok})")

    if errors:
        print("FAIL trajectory fixture:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"OK fixture={fix.get('id')} steps={len(steps)} path={ids}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
