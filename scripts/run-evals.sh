#!/usr/bin/env bash
# Static eval harness — validates evals.json structure and prints smoke/full suites.
# Does NOT call a model (no API cost). Use for CI + agent smoke of the eval bank.
#
# Usage:
#   bash scripts/run-evals.sh              # smoke subset
#   bash scripts/run-evals.sh --full       # all scenarios
#   bash scripts/run-evals.sh --list       # ids + prompts only
#   bash scripts/run-evals.sh --json       # machine summary
#   bash scripts/run-evals.sh --file path  # validate another bank against this repo
#   bash scripts/run-evals.sh --live [...] # OPT-IN live model smoke via claude -p
#                                          # (costs tokens; never part of default CI;
#                                          # remaining args pass to run-live-evals.py,
#                                          # e.g. --live --compare --model haiku)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EVALS="$ROOT/evals/evals.json"
MODE=smoke
LIST=0
JSON=0

# --live hands off to the live model-in-the-loop runner. Explicit opt-in only:
# it spends provider tokens and requires an authenticated `claude` binary.
if [[ "${1:-}" == "--live" ]]; then
  shift
  exec python3 "$ROOT/scripts/run-live-evals.py" "$@"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full) MODE=full ;;
    --smoke) MODE=smoke ;;
    --list) LIST=1 ;;
    --json) JSON=1 ;;
    --file)
      [[ $# -ge 2 ]] || { echo "--file requires a path" >&2; exit 2; }
      EVALS="$2"
      shift
      ;;
    -h|--help)
      echo "Usage: bash scripts/run-evals.sh [--smoke|--full] [--list] [--json] [--file path]"
      echo "       bash scripts/run-evals.sh --live [runner args]   # opt-in live model smoke (costs tokens)"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

# smoke = first 8 evals (or tagged smoke when present)
python3 - "$EVALS" "$MODE" "$LIST" "$JSON" "$ROOT" <<'PY'
import json, sys
from pathlib import Path

path, mode, list_only, as_json, root = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4] == "1", Path(sys.argv[5])
try:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
except (OSError, UnicodeError, json.JSONDecodeError) as exc:
    print(f"FAIL eval bank: {exc}")
    sys.exit(1)
if not isinstance(data, dict):
    print("FAIL eval bank: root must be an object")
    sys.exit(1)
evals = data.get("evals")
if not isinstance(evals, list):
    print("FAIL eval bank: evals must be an array")
    sys.exit(1)
errors = []
sys.path.insert(0, str(root / "scripts"))
from evidence_path import safe_path

if data.get("skill_name") != "engineer":
    errors.append("skill_name must equal engineer")
if not evals:
    errors.append("no evals")

allowed_keys = {"id", "prompt", "expected_output", "assertions", "files"}
prompts = set()
for i, e in enumerate(evals):
    if not isinstance(e, dict):
        errors.append(f"evals[{i}] not object")
        continue
    unknown = set(e) - allowed_keys
    if unknown:
        errors.append(f"evals[{i}] unknown keys: {sorted(unknown)}")
    for k in ("id", "prompt", "expected_output", "assertions", "files"):
        if k not in e:
            errors.append(f"evals[{i}] missing {k}")
    if not isinstance(e.get("id"), int) or isinstance(e.get("id"), bool) or e.get("id", 0) < 1:
        errors.append(f"evals[{i}] id must be a positive integer")
    for k in ("prompt", "expected_output"):
        if not isinstance(e.get(k), str) or not e[k].strip():
            errors.append(f"evals[{i}] {k} empty")
    prompt = e.get("prompt")
    if isinstance(prompt, str):
        if prompt in prompts:
            errors.append(f"evals[{i}] duplicate prompt")
        prompts.add(prompt)
    asserts = e.get("assertions") or []
    if not isinstance(asserts, list) or not asserts or any(not isinstance(x, str) or not x.strip() for x in asserts):
        errors.append(f"evals[{i}] assertions empty")
    elif len(asserts) != len(set(asserts)):
        errors.append(f"evals[{i}] duplicate assertions")
    files = e.get("files")
    if not isinstance(files, list) or any(not isinstance(x, str) or not x for x in files):
        errors.append(f"evals[{i}] files must be an array of paths")
    else:
        for file in files:
            target = safe_path(file, root)
            if target is None or not target.is_file():
                errors.append(f"evals[{i}] missing or unsafe file: {file}")
ids = [e.get("id") for e in evals if isinstance(e, dict) and type(e.get("id")) is int]
if len(ids) != len(set(ids)):
    errors.append("duplicate eval ids")
if ids != list(range(1, len(evals) + 1)):
    errors.append("eval ids must be contiguous and ordered from 1")

# suite selection
smoke_ids = {1, 2, 7, 8, 12, 15, 20, 28, 37, 40, 63, 64, 67, 70, 71, 72, 73, 74, 75, 76, 77, 78}
if mode == "smoke":
    selected = [e for e in evals if isinstance(e, dict) and type(e.get("id")) is int and e.get("id") in smoke_ids]
    if len(selected) < 5:
        selected = evals[:8]
else:
    selected = evals

if errors:
    print("FAIL eval bank:")
    for err in errors:
        print(f"  - {err}")
    sys.exit(1)

if as_json:
    print(json.dumps({
        "ok": True,
        "skill": data.get("skill_name"),
        "mode": mode,
        "total": len(evals),
        "selected": len(selected),
        "ids": [e.get("id") for e in selected if isinstance(e, dict)],
    }, indent=2))
    sys.exit(0)

print(f"engineer evals — {data.get('skill_name')} · mode={mode}")
print(f"bank={len(evals)} selected={len(selected)}")
print("---")
for e in selected:
    if not isinstance(e, dict):
        continue
    eid = e.get("id")
    prompt = str(e.get("prompt") or "")[:90]
    n_a = len(e.get("assertions") or [])
    if list_only:
        print(f"[{eid}] {prompt}")
    else:
        print(f"[{eid}] assertions={n_a}")
        print(f"  prompt: {prompt}")
        print(f"  expect: {str(e.get('expected_output') or '')[:100]}…")
print("---")
print("OK — eval bank structure valid (static harness; no model run)")
print("To run live model evals, mount SKILL.md in your agent and use prompts from --list")
PY
