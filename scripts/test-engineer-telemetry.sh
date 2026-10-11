#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECORDER="$ROOT/scripts/record-engineer-telemetry.py"
VALIDATOR="$ROOT/scripts/validate-engineer-telemetry.py"
SUMMARY="$ROOT/scripts/summarize-engineer-telemetry.py"
CAPTURE="$ROOT/templates/agentic/skill-eval-capture.sample.json"
GRADE="$ROOT/templates/agentic/skill-eval-grade.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 "$RECORDER" "$CAPTURE" --root "$ROOT" --output "$TMP/events.jsonl" >/dev/null
python3 "$VALIDATOR" "$TMP/events.jsonl" >/dev/null
python3 "$SUMMARY" "$TMP/events.jsonl" >"$TMP/summary.json"
python3 - "$TMP/summary.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d["events"]==1 and d["graded_events"]==0
assert d["behavioral_pass_rate"] is None and d["capture_success_rate"]==1 and d["ungraded_capture_backlog"]==1
PY

python3 "$RECORDER" "$GRADE" --root "$ROOT" --output "$TMP/events.jsonl" >/dev/null
# Re-recording the same canonical grade is idempotent.
python3 "$RECORDER" "$GRADE" --root "$ROOT" --output "$TMP/events.jsonl" >/dev/null
python3 "$SUMMARY" "$TMP/events.jsonl" >"$TMP/graded-summary.json"
python3 - "$TMP/graded-summary.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); assert d["events"]==2 and d["graded_events"]==1
assert d["behavioral_pass_rate"]==1 and d["safety_failures"]==0 and d["ungraded_capture_backlog"]==0
assert d["event_kinds"]=={"skill_eval_capture":1,"skill_eval_grade":1}
PY

mutate() {
  local name="$1" expression="$2"
  python3 - "$TMP/events.jsonl" "$TMP/$name.jsonl" "$expression" <<'PY'
import json,sys
d=json.loads(open(sys.argv[1]).readline()); exec(sys.argv[3],{"d":d}); open(sys.argv[2],"w").write(json.dumps(d)+"\n")
PY
  if python3 "$VALIDATOR" "$TMP/$name.jsonl" >/dev/null 2>&1; then
    echo "expected telemetry rejection: $name" >&2
    exit 1
  fi
}

mutate prompt_content 'd["prompt"]="private prompt"'
mutate identity 'd["user"]={"email":"person@example.com"}'
mutate remote_export 'd["privacy"]["export"]="otlp"'
mutate content_enabled 'd["privacy"]["content_recorded"]=True'
mutate false_graded 'd["quality"]["grading_required"]=False'
mutate bad_event_id 'd["event_id"]="session-123"'
mutate high_cardinality_model 'd["host"]["model"]="x"*129'
mutate leaked_path 'd["source_path"]="private/file"'

python3 - "$TMP/events.jsonl" "$TMP/duplicate.jsonl" <<'PY'
import sys
lines=open(sys.argv[1], encoding="utf-8").readlines(); open(sys.argv[2],"w",encoding="utf-8").writelines(lines+[lines[-1]])
PY
if python3 "$VALIDATOR" "$TMP/duplicate.jsonl" >/dev/null 2>&1; then
  echo "expected duplicate telemetry rejection" >&2
  exit 1
fi

printf '%s\n' '{"schema_version":1}' >"$TMP/legacy.jsonl"
if python3 "$RECORDER" "$CAPTURE" --root "$ROOT" --output "$TMP/legacy.jsonl" >/dev/null 2>&1; then
  echo "legacy ledger unexpectedly accepted an append" >&2
  exit 1
fi
if [[ "$(wc -l < "$TMP/legacy.jsonl" | tr -d ' ')" != "1" ]]; then
  echo "legacy ledger was mutated before rejection" >&2
  exit 1
fi

cp "$TMP/events.jsonl" "$TMP/ledger-victim.jsonl"
victim_before="$(shasum -a 256 "$TMP/ledger-victim.jsonl" | cut -d' ' -f1)"
ln -s "$TMP/ledger-victim.jsonl" "$TMP/ledger-link.jsonl"
if python3 "$RECORDER" "$CAPTURE" --root "$ROOT" --output "$TMP/ledger-link.jsonl" >/dev/null 2>&1; then
  echo "symlinked telemetry ledger unexpectedly accepted an append" >&2
  exit 1
fi
victim_after="$(shasum -a 256 "$TMP/ledger-victim.jsonl" | cut -d' ' -f1)"
test "$victim_before" = "$victim_after"

printf 'project-owned\n' >"$TMP/lock-victim"
ln -s "$TMP/lock-victim" "$TMP/locked.jsonl.lock"
if python3 "$RECORDER" "$CAPTURE" --root "$ROOT" --output "$TMP/locked.jsonl" >/dev/null 2>&1; then
  echo "symlinked telemetry lock unexpectedly accepted" >&2
  exit 1
fi
grep -q '^project-owned$' "$TMP/lock-victim"
test ! -e "$TMP/locked.jsonl"

python3 "$RECORDER" "$CAPTURE" --root "$ROOT" --output "$TMP/concurrent.jsonl" >/dev/null &
capture_pid=$!
python3 "$RECORDER" "$GRADE" --root "$ROOT" --output "$TMP/concurrent.jsonl" >/dev/null &
grade_pid=$!
wait "$capture_pid"
wait "$grade_pid"
python3 "$VALIDATOR" "$TMP/concurrent.jsonl" >/dev/null
test "$(wc -l < "$TMP/concurrent.jsonl" | tr -d ' ')" = "2"

for _ in 1 2 3 4 5 6 7 8; do
  python3 "$RECORDER" "$CAPTURE" --root "$ROOT" --output "$TMP/idempotent-concurrent.jsonl" >/dev/null &
done
wait
python3 "$VALIDATOR" "$TMP/idempotent-concurrent.jsonl" >/dev/null
test "$(wc -l < "$TMP/idempotent-concurrent.jsonl" | tr -d ' ')" = "1"

if python3 "$RECORDER" "$ROOT/templates/agentic/skill-eval-job.sample.json" --root "$ROOT" --output "$TMP/bad.jsonl" >/dev/null 2>&1; then
  echo "invalid capture unexpectedly produced telemetry" >&2
  exit 1
fi

echo "engineer telemetry fixtures passed"
