#!/usr/bin/env bash
# Test the false-done scanner (scripts/scan-false-done.sh) against a scratch git
# repo: clean changes pass, skipped tests and not-implemented markers BLOCK,
# deferral markers and test-edits-with-impl WARN.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SC="$ROOT/scripts/scan-false-done.sh"
FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }

echo "test scan-false-done"
echo "---"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/fdtest.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
git init -q
git config user.email t@t.t
git config user.name t
git config commit.gpgsign false   # scratch repo: never touch the real signer

mkdir -p src tests
printf 'export const add=(a,b)=>a+b;\n' > src/math.js
printf 'test("add",()=>{});\n' > tests/math.test.js
git add -A && git commit -qm base

# Capture the scanner's exit code without tripping `set -e` (BLOCK = exit 2 is
# an expected outcome here, not a test failure).
run() { local rc=0; bash "$SC" --base HEAD~1 "$@" >/dev/null 2>&1 || rc=$?; echo "$rc"; }

# 1. clean change → exit 0
printf 'export const sub=(a,b)=>a-b;\n' >> src/math.js
git add -A && git commit -qm c1
[[ "$(run)" == "0" ]] && pass "clean change → exit 0" || fail "clean change should exit 0"

# 2. skipped test → BLOCK exit 2
printf 'it.skip("later",()=>{});\n' >> tests/math.test.js
git add -A && git commit -qm c2
[[ "$(run)" == "2" ]] && pass "skipped test → BLOCK (exit 2)" || fail "skipped test should BLOCK (exit 2)"

# 3. not-implemented in prod → BLOCK exit 2
printf 'export function mul(){throw new Error("not implemented");}\n' >> src/math.js
git add -A && git commit -qm c3
[[ "$(run)" == "2" ]] && pass "not-implemented → BLOCK (exit 2)" || fail "not-implemented should BLOCK (exit 2)"

# 4. focused test (xit) → BLOCK (verifies the \b→boundary fix)
printf 'xit("focus",()=>{});\n' >> tests/math.test.js
git add -A && git commit -qm c4
[[ "$(run)" == "2" ]] && pass "xit focused test → BLOCK (exit 2)" || fail "xit should BLOCK (exit 2)"

# 5. TODO in prod → WARN (exit 0 non-strict, exit 1 strict) — verifies \b fix
printf 'export const div=(a,b)=>a/b; // TODO handle zero\n' >> src/math.js
git add -A && git commit -qm c5
[[ "$(run)" == "0" ]] && pass "TODO → exit 0 non-strict" || fail "TODO should exit 0 non-strict"
[[ "$(run --strict)" == "1" ]] && pass "TODO → exit 1 under --strict" || fail "TODO should exit 1 under --strict"

# 6. JSON output is well-formed (capture first — scanner exits 2 on BLOCK, which
# pipefail would otherwise surface as a pipeline failure).
printf 'it.skip("x",()=>{});\n' >> tests/math.test.js
git add -A && git commit -qm c6
JSON_OUT="$(bash "$SC" --base HEAD~1 --json 2>/dev/null || true)"
if printf '%s' "$JSON_OUT" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert isinstance(d["block"],list) and isinstance(d["warn"],list) and len(d["block"])>=1' 2>/dev/null; then
  pass "JSON output is well-formed with the expected BLOCK finding"
else
  fail "JSON output should be valid JSON with block/warn arrays"
fi

echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
  echo "scan-false-done: all tests passed"
  exit 0
else
  echo "scan-false-done: $FAILURES failure(s)"
  exit 1
fi
