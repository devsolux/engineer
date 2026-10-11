#!/usr/bin/env bash
# Lightweight health score for a target app or the engineer skill package.
# Inspired by gstack health — wraps existing tools, no daemon.
#
# Usage:
#   bash /path/to/engineer/scripts/engineer-health.sh [--profile auto|app|skill] [--json] [--strict]
set -euo pipefail

JSON=0
STRICT=0
PROFILE=auto
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) JSON=1 ;;
    --strict) STRICT=1 ;;
    --profile=*) PROFILE="${1#*=}" ;;
    --profile)
      [[ $# -ge 2 ]] || { echo "--profile requires a value" >&2; exit 2; }
      PROFILE="$2"
      shift
      ;;
    -h|--help)
      echo "Usage: engineer-health.sh [--profile auto|app|skill] [--json] [--strict]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [[ "$PROFILE" != "auto" && "$PROFILE" != "app" && "$PROFILE" != "skill" ]]; then
  echo "Unknown profile: $PROFILE (expected auto, app, or skill)" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "$PROFILE" == "auto" ]]; then
  if [[ -f SKILL.md && -d references && -d commands && -f scripts/validate-repo.sh ]]; then
    PROFILE=skill
  else
    PROFILE=app
  fi
fi

SCORE=0
MAX=0
RESULTS=()

check() {
  local name="$1"
  local weight="$2"
  shift 2
  MAX=$((MAX + weight))
  if "$@" >/dev/null 2>&1; then
    SCORE=$((SCORE + weight))
    RESULTS+=("pass|$name|$weight")
    [[ "$JSON" -eq 0 ]] && echo "  ✓ $name (+$weight)"
  else
    RESULTS+=("fail|$name|$weight")
    [[ "$JSON" -eq 0 ]] && echo "  ✗ $name (0/$weight)"
  fi
  return 0
}

[[ "$JSON" -eq 0 ]] && echo "engineer health — $(pwd) [$PROFILE]" && echo "---"

if [[ "$PROFILE" == "skill" ]]; then
  check "repository integrity" 1 bash "$SCRIPT_DIR/validate-repo.sh"
  check "all discovered offline fixture suites" 2 python3 "$SCRIPT_DIR/run-tests.py"
  check "eval bank" 2 bash "$SCRIPT_DIR/run-evals.sh" --full
fi

# Typecheck
if [[ "$PROFILE" == "app" && -f tsconfig.json ]]; then
  if command -v pnpm >/dev/null 2>&1 && [[ -f pnpm-lock.yaml ]]; then
    check "tsc (pnpm)" 3 pnpm exec tsc --noEmit
  else
    check "local tsc" 3 ./node_modules/.bin/tsc --noEmit
  fi
fi

# Lint
if [[ "$PROFILE" == "app" ]] && { [[ -f eslint.config.mjs ]] || [[ -f eslint.config.js ]] || [[ -f .eslintrc.json ]]; }; then
  if command -v pnpm >/dev/null 2>&1 && [[ -f pnpm-lock.yaml ]]; then
    check "eslint (pnpm)" 2 pnpm exec eslint . --max-warnings=50
  else
    check "local eslint" 2 ./node_modules/.bin/eslint . --max-warnings=50
  fi
fi

# Unit tests
if [[ "$PROFILE" == "app" && -f package.json ]] && grep -q '"test"' package.json 2>/dev/null; then
  if [[ -f pnpm-lock.yaml ]]; then
    check "pnpm test" 2 pnpm test
  elif [[ -f yarn.lock ]]; then
    check "yarn test" 2 yarn test
  else
    check "npm test" 2 npm test
  fi
fi

# Python
if [[ "$PROFILE" == "app" ]] && { [[ -f pyproject.toml ]] || [[ -f uv.lock ]]; }; then
  if command -v ruff >/dev/null 2>&1; then
    check "ruff" 2 ruff check .
  fi
  if [[ -f uv.lock ]] && command -v uv >/dev/null 2>&1; then
    check "uv.lock present" 1 test -f uv.lock
  fi
fi

# Rust
if [[ "$PROFILE" == "app" && -f Cargo.toml ]]; then
  check "cargo test" 3 cargo test --quiet
  check "cargo build" 1 cargo build --quiet
fi

# engineer scan if script reachable
if [[ "$PROFILE" == "app" && -f "$SCRIPT_DIR/engineer-scan.sh" ]]; then
  check "engineer-scan --backend" 2 bash "$SCRIPT_DIR/engineer-scan.sh" --backend --quiet
fi

# Lockfiles / hygiene
[[ "$PROFILE" == "app" && -f package.json && ! -f pnpm-lock.yaml && ! -f package-lock.json && ! -f yarn.lock ]] && \
  { RESULTS+=("fail|js lockfile|1"); MAX=$((MAX+1)); [[ "$JSON" -eq 0 ]] && echo "  ✗ js lockfile"; } || true

if [[ "$MAX" -eq 0 ]]; then
  [[ "$JSON" -eq 0 ]] && echo "No recognizable project tools found"
  [[ "$JSON" -eq 1 ]] && echo '{"ok":false,"score":0,"max":0,"note":"no tools"}'
  exit 1
fi

# 0–10 scale
TEN=$(python3 -c "print(round(10.0 * $SCORE / $MAX, 1))")

if [[ "$JSON" -eq 1 ]]; then
  python3 -c "
import json
results = '''$(printf '%s\n' "${RESULTS[@]}")'''.strip().splitlines()
items = []
for r in results:
    if not r: continue
    st, name, w = r.split('|', 2)
    items.append({'status': st, 'name': name, 'weight': int(w)})
print(json.dumps({'ok': $SCORE == $MAX, 'score_0_10': $TEN, 'raw': $SCORE, 'max': $MAX, 'checks': items}, indent=2))
"
else
  echo "---"
  echo "score ${TEN}/10  (raw ${SCORE}/${MAX})"
fi

# Health remains advisory unless explicitly used as a strict gate.
if [[ "$STRICT" -eq 1 && "$SCORE" -ne "$MAX" ]]; then
  exit 1
fi
exit 0
