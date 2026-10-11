#!/usr/bin/env bash
# Fixture tests for engineer-scan.sh
# Usage: bash scripts/test-scan.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCAN="$ROOT/scripts/engineer-scan.sh"
FIX="$ROOT/scripts/fixtures"
FAILURES=0

run_expect() {
  local label="$1"
  local dir="$2"
  local expect_exit="$3" # 0 or 1
  local flags="${4:-}"
  local out
  local code=0
  set +e
  # shellcheck disable=SC2086
  out=$(cd "$dir" && bash "$SCAN" $flags 2>&1)
  code=$?
  set -e
  if [[ "$code" -eq "$expect_exit" ]]; then
    echo "  ✓ $label (exit $code)"
  else
    echo "  ✗ $label — expected exit $expect_exit got $code"
    echo "$out" | tail -20
    FAILURES=$((FAILURES + 1))
  fi
}

echo "engineer test-scan — fixtures"
echo "---"

# Exercise the portable grep fallback even on developer hosts that have rg.
export ENGINEER_FORCE_GREP=1

# Pass fixture: no secrets, rate-limited sensitive action → should pass backend
run_expect "pass fixture --backend" "$FIX/pass" 0 "--backend --quiet"

# Fail fixture: secret literal → always fails
run_expect "fail fixture secrets (default)" "$FIX/fail" 1 "--quiet"

# Fail fixture: rate-limit under --strict should fail (even if secrets also fail — exit 1)
run_expect "fail fixture --backend --strict" "$FIX/fail" 1 "--backend --strict --quiet"

run_expect "pass fixture --design" "$FIX/pass" 0 "--design --quiet"
run_expect "fail-design hardcoded palette" "$FIX/fail-design" 1 "--design --quiet"
run_expect "fail-taste tells warn-only" "$FIX/fail-taste" 0 "--design --quiet"
run_expect "fail-taste tells fail --strict" "$FIX/fail-taste" 1 "--design --strict --quiet"

# JSON mode produces ok field
JSON=$(cd "$FIX/pass" && bash "$SCAN" --backend --json 2>/dev/null | tail -1)
if echo "$JSON" | grep -q '"ok":true'; then
  echo "  ✓ pass fixture --json ok:true"
else
  echo "  ✗ pass fixture --json"
  echo "    $JSON"
  FAILURES=$((FAILURES + 1))
fi

echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
  echo "OK — all fixture scans passed"
  exit 0
fi
echo "FAILED — $FAILURES fixture check(s)"
exit 1
