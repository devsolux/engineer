#!/usr/bin/env bash
# Offline fixtures for the live eval runner (scripts/run-live-evals.py).
# Uses a shimmed `claude` binary — no model call, no token spend.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNNER="$ROOT/scripts/run-live-evals.py"
BANK="$ROOT/evals/live-smoke.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1. Static: the shipped live-smoke bank validates and lists without a model.
python3 "$RUNNER" --list >/dev/null
python3 "$RUNNER" --list --scenarios root-cause-retry,negative-prose-deslop >/dev/null
if python3 "$RUNNER" --list --scenarios not-a-scenario >/dev/null 2>&1; then
  echo "expected unknown scenario id to fail" >&2; exit 1
fi

# 2. Shim host: routes correctly (marker only when skills enabled AND prompt says engineer),
#    and echoes enough scenario language for assert_any to hit.
cat > "$TMP/claude" <<'SHIM'
#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
prompt = args[args.index("-p") + 1]
skills_enabled = "--disable-slash-commands" not in args
lower = prompt.lower()
text = ("Reproduce first, then root cause via the causal chain. Zod at the boundary; "
        "OKLCH semantic tokens; tracing with graceful shutdown; key decision with tradeoff "
        "and non-goals stated; portfolio consumer check.")
if skills_enabled and "engineer" in lower and "[routing-probe:alpha]" in prompt:
    text += "\n\nENGINEER_ROUTING_ACTIVE_v1"
json.dump({"type": "result", "result": text, "total_cost_usd": 0.0, "num_turns": 1}, sys.stdout)
SHIM
chmod +x "$TMP/claude"

# Compare mode: all with-skill rows pass, baseline control shows no marker leak, lift computed.
OUT="$(python3 "$RUNNER" --compare --claude-bin "$TMP/claude" --report-dir "$TMP/runs" --timeout 30)"
echo "$OUT" | grep -q "OK — live eval run passed" || { echo "compare run should pass" >&2; exit 1; }
echo "$OUT" | grep -q "lift_strict" || { echo "compare run must report lift" >&2; exit 1; }
REPORT="$(find "$TMP/runs" -name '*.json' | head -1)"
python3 - "$REPORT" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
rows = r["scenarios"]
assert r["arms"] == ["with-skill", "baseline"], r["arms"]
assert all(x["passed"] for x in rows if x["arm"] == "with-skill"), "with-skill rows must pass"
assert not any(x["activation_observed"] for x in rows if x["arm"] == "baseline"), "baseline must never activate"
assert r["summary"]["lift_strict"] > 0, "positive scenarios must show strict lift"
PY

# 3. Leaky shim: marker in the baseline arm must fail the run.
cat > "$TMP/claude-leak" <<'SHIM'
#!/usr/bin/env python3
import json, sys
json.dump({"type": "result", "result": "root cause reproduce zod portfolio consumer\nENGINEER_ROUTING_ACTIVE_v1",
           "total_cost_usd": 0.0, "num_turns": 1}, sys.stdout)
SHIM
chmod +x "$TMP/claude-leak"
if python3 "$RUNNER" --baseline --scenarios core-signup-auth --claude-bin "$TMP/claude-leak" --report-dir "$TMP/runs" >/dev/null 2>&1; then
  echo "baseline marker leak must fail" >&2; exit 1
fi

# 4. Silent-compliance shim: retry scenario without diagnosis language must fail asserts.
#    (known_gap cleared so the assert miss gates the exit code.)
python3 -c "
import json
p = json.load(open('$BANK'))
for s in p['scenarios']:
    s.pop('known_gap', None)
json.dump(p, open('$TMP/strict.json', 'w'))
"
cat > "$TMP/claude-comply" <<'SHIM'
#!/usr/bin/env python3
import json, sys
json.dump({"type": "result", "result": "Sure. Wrap the payment call in a loop with backoff.\n\nENGINEER_ROUTING_ACTIVE_v1",
           "total_cost_usd": 0.0, "num_turns": 1}, sys.stdout)
SHIM
chmod +x "$TMP/claude-comply"
if python3 "$RUNNER" --file "$TMP/strict.json" --scenarios root-cause-retry --claude-bin "$TMP/claude-comply" --report-dir "$TMP/runs" >/dev/null 2>&1; then
  echo "silent retry compliance must fail assert grading" >&2; exit 1
fi

# 4b. Same shim against the shipped bank: root-cause-retry is a tracked known_gap (xfail),
#     so the miss reports without gating the exit code.
OUT="$(python3 "$RUNNER" --scenarios root-cause-retry --claude-bin "$TMP/claude-comply" --report-dir "$TMP/runs")"
echo "$OUT" | grep -q "XFAIL — tracked routing gap" || { echo "known_gap miss must report as XFAIL" >&2; exit 1; }
echo "$OUT" | grep -q "OK — live eval run passed" || { echo "known_gap miss must not gate exit" >&2; exit 1; }

# 5. Hard cap: a bank with 13 scenarios must refuse to run live.
python3 - "$BANK" "$TMP/big.json" <<'PY'
import json, sys
bank = json.load(open(sys.argv[1]))
s = bank["scenarios"]
while len(s) < 13:
    c = dict(s[0]); c["id"] = f"pad-{len(s)}"; c["prompt"] = s[0]["prompt"] + f" pad {len(s)}"; s.append(c)
json.dump(bank, open(sys.argv[2], "w"))
PY
if python3 "$RUNNER" --file "$TMP/big.json" --claude-bin "$TMP/claude" --report-dir "$TMP/runs" >/dev/null 2>&1; then
  echo "hard scenario cap must refuse >12 scenarios" >&2; exit 1
fi

# 6. Invalid banks must fail validation.
invalid_case() {
  local name="$1" mutation="$2"
  python3 -c "import json; p=json.load(open('$BANK')); $mutation; json.dump(p,open('$TMP/$name.json','w'))"
  if python3 "$RUNNER" --list --file "$TMP/$name.json" >/dev/null 2>&1; then
    echo "expected invalid live-smoke bank to fail: $name" >&2; exit 1
  fi
}
invalid_case dup_id "p['scenarios'][1]['id']=p['scenarios'][0]['id']"
invalid_case bad_expect "p['scenarios'][0]['expect_activation']='yes'"
invalid_case unknown_key "p['scenarios'][0]['golden']='x'"
invalid_case bad_source "p['scenarios'][0]['source_eval']=99999"
invalid_case bad_known_gap "p['scenarios'][0]['known_gap']='yes'"
invalid_case no_marker "del p['activation_marker']"

echo "live eval fixtures passed"
