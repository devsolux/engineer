#!/usr/bin/env bash
# Test the skill-eval rebinder (scripts/rebind-skill-eval.py) in an isolated
# tree: a version bump and a corrupted content-chain digest are both detected by
# --check and fixed by a rebind that the real grader then accepts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOL="$ROOT/scripts/rebind-skill-eval.py"
FAILURES=0
pass() { echo "  ✓ $1"; }
fail() { echo "  ✗ $1"; FAILURES=$((FAILURES + 1)); }
rc() { local c=0; "$@" >/dev/null 2>&1 || c=$?; echo "$c"; }

echo "test rebind-skill-eval"
echo "---"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/rebind.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

# Isolated root: a real copy of the runtime-package include set (the bundle
# walker rejects symlinks by design, so everything must be a real file). The
# skill-eval samples are excluded from the bundle hash, so editing them never
# perturbs it. evals/ is copied for the bank hash.
for e in SKILL.md COMPAT.md agents commands references scripts templates evals; do
  [ -e "$ROOT/$e" ] && cp -r "$ROOT/$e" "$WORK/$e"
done

printf "user-owned\n" > "$WORK/.rebind-verify.json"

# 1. Baseline rebind → bound + grader-verified.
[[ "$(rc python3 "$TOOL" --root "$WORK")" == "0" ]] && pass "baseline rebind → verified (exit 0)" || fail "baseline rebind should exit 0"
[[ "$(rc python3 "$TOOL" --check --root "$WORK")" == "0" ]] && pass "--check on bound tree → exit 0" || fail "--check bound should exit 0"

[[ "$(cat "$WORK/.rebind-verify.json")" == "user-owned" ]] && pass "pre-existing verifier file preserved" || fail "user verifier file was changed"

# 2. Version bump drifts the chain → --check exit 1 → rebind fixes → --check exit 0.
python3 - "$WORK/SKILL.md" <<'PY'
import re, sys
p = sys.argv[1]
t = open(p).read()
open(p, "w").write(re.sub(r'(version:\s*")[^"]+(")', r'\g<1>99.0.0-test\g<2>', t, count=1))
PY
[[ "$(rc python3 "$TOOL" --check --root "$WORK")" == "1" ]] && pass "version bump → --check detects drift (exit 1)" || fail "version bump should be detected (exit 1)"
[[ "$(rc python3 "$TOOL" --root "$WORK")" == "0" ]] && pass "rebind after version bump → verified (exit 0)" || fail "rebind after bump should exit 0"
[[ "$(rc python3 "$TOOL" --check --root "$WORK")" == "0" ]] && pass "--check clean after rebind → exit 0" || fail "--check should be clean after rebind"

# 3. Corrupted content-chain digest → --check exit 1 → rebind fixes.
python3 - "$WORK/templates/agentic/skill-eval-capture.sample.json" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["job"]["sha256"] = "0" * 64
json.dump(d, open(p, "w"), indent=2)
PY
[[ "$(rc python3 "$TOOL" --check --root "$WORK")" == "1" ]] && pass "corrupt chain digest → --check detects (exit 1)" || fail "corrupt chain digest should be detected (exit 1)"
[[ "$(rc python3 "$TOOL" --root "$WORK")" == "0" ]] && pass "rebind fixes corrupt chain (exit 0)" || fail "rebind should fix corrupt chain"

# 4. A stale derived grade must be detected even with a valid capture chain.
python3 - "$WORK/templates/agentic/skill-eval-grade.sample.json" <<'PYGRADE'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["artifact_sha256"]["output"] = "f" * 64
with open(p, "w") as out:
    json.dump(d, out, indent=2)
PYGRADE
[[ "$(rc python3 "$TOOL" --check --root "$WORK")" == "1" ]] && pass "grade replay drift detected" || fail "stale grade should be detected"
[[ "$(rc python3 "$TOOL" --root "$WORK")" == "0" ]] && pass "grade replay repaired" || fail "grade replay repair failed"
[[ "$(rc python3 "$WORK/scripts/validate-skill-eval-grade.py" "$WORK/templates/agentic/skill-eval-grade.sample.json" --root "$WORK")" == "0" ]] && pass "stored grade passes canonical replay" || fail "stored grade does not replay"

# 5. Refuse rebinding data that claims to be captured, rather than illustrative.
python3 - "$WORK/templates/agentic/skill-eval-capture.sample.json" <<'PYCAP'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d["capture_kind"] = "captured_run"
with open(p, "w") as out:
    json.dump(d, out, indent=2)
PYCAP
before="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$WORK/templates/agentic/skill-eval-capture.sample.json")"
[[ "$(rc python3 "$TOOL" --root "$WORK")" == "2" ]] && pass "captured evidence refused" || fail "captured evidence must not be rebound"
after="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$WORK/templates/agentic/skill-eval-capture.sample.json")"
[[ "$before" == "$after" ]] && pass "captured input preserved" || fail "captured input was modified"

echo "---"
if [[ "$FAILURES" -eq 0 ]]; then
  echo "rebind-skill-eval: all tests passed"
  exit 0
else
  echo "rebind-skill-eval: $FAILURES failure(s)"
  exit 1
fi
