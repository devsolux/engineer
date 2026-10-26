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

# Rust fixtures: lints table, deny(warnings), unwrap/unsafe/leftover tiers, auto-enable
run_expect "pass-rust --rust" "$FIX/pass-rust" 0 "--rust --quiet"
run_expect "pass-rust --rust --strict" "$FIX/pass-rust" 0 "--rust --strict --quiet"
run_expect "warn-rust unwrap/unsafe/dbg warn-only" "$FIX/warn-rust" 0 "--rust --quiet"
run_expect "warn-rust fails --strict" "$FIX/warn-rust" 1 "--rust --strict --quiet"
run_expect "fail-rust deny(warnings) fails" "$FIX/fail-rust" 1 "--rust --quiet"
run_expect "fail-rust auto-enabled by Cargo.toml" "$FIX/fail-rust" 1 "--quiet"

RS_WARN_OUT=$(cd "$FIX/warn-rust" && bash "$SCAN" --rust 2>&1 || true)
for id in RS-UNWRAP RS-UNSAFE-SAFETY RS-DEBUG-LEFTOVER; do
  if echo "$RS_WARN_OUT" | grep -q "$id"; then
    echo "  ✓ warn-rust reports $id"
  else
    echo "  ✗ warn-rust missing $id"
    FAILURES=$((FAILURES + 1))
  fi
done
if echo "$RS_WARN_OUT" | grep -q 'v\.unwrap()'; then
  echo "  ✗ warn-rust reported the unwrap inside #[cfg(test)] mod tests"
  FAILURES=$((FAILURES + 1))
else
  echo "  ✓ warn-rust ignores unwrap inside #[cfg(test)] mod tests"
fi
RS_FAIL_OUT=$(cd "$FIX/fail-rust" && bash "$SCAN" --rust 2>&1 || true)
for id in RS-LINTS RS-DENY-WARNINGS; do
  if echo "$RS_FAIL_OUT" | grep -q "$id"; then
    echo "  ✓ fail-rust reports $id"
  else
    echo "  ✗ fail-rust missing $id"
    FAILURES=$((FAILURES + 1))
  fi
done
RS_PASS_OUT=$(cd "$FIX/pass-rust" && bash "$SCAN" --rust --strict 2>&1 || true)
if echo "$RS_PASS_OUT" | grep -q 'RS-'; then
  echo "  ✗ pass-rust raised an RS-* signal"
  echo "$RS_PASS_OUT" | grep 'RS-'
  FAILURES=$((FAILURES + 1))
else
  echo "  ✓ pass-rust raises no RS-* signal"
fi

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
