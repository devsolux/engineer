#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GRADER="$ROOT/scripts/grade-skill-eval-capture.py"
VALIDATOR="$ROOT/scripts/validate-skill-eval-grade.py"
COMPARATOR="$ROOT/scripts/compare-skill-eval-grades.py"
COMPARISON_VALIDATOR="$ROOT/scripts/validate-skill-eval-comparison.py"
CAPTURE="$ROOT/templates/agentic/skill-eval-capture.sample.json"
ORACLE="$ROOT/templates/agentic/skill-eval-oracle.sample.json"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cd "$ROOT"
python3 "$GRADER" "$CAPTURE" --oracle "$ORACLE" --root "$ROOT" --output "$TMP/grade.json"
ln -s "$CAPTURE" "$TMP/capture-link.json"
if python3 "$GRADER" "$TMP/capture-link.json" --oracle "$ORACLE" --root "$ROOT" --output "$TMP/symlink-grade.json" >/dev/null 2>&1; then
  echo "expected symlinked capture rejection" >&2
  exit 1
fi
python3 "$VALIDATOR" "$TMP/grade.json" --root "$ROOT" >/dev/null
python3 - "$TMP/grade.json" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding="utf-8"))
assert d["summary"]["behavioral_pass"] is True
assert d["summary"]["score"] == 1
assert d["promotion_eligible"] is False
PY

python3 - "$TMP/grade.json" "$TMP/tampered.json" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding="utf-8")); d["summary"]["behavioral_pass"] = False
json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
if python3 "$VALIDATOR" "$TMP/tampered.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "expected tampered grade rejection" >&2
  exit 1
fi

python3 - "$ROOT/templates/agentic/skill-eval-comparison.sample.json" "$TMP/grade.json" "$TMP/comparison.json" <<'PY'
import json, pathlib, sys
sample, grade, target = sys.argv[1:]
d=json.load(open(sample, encoding="utf-8"))
relative=pathlib.Path(grade).relative_to(pathlib.Path(sample).parents[2]).as_posix() if False else None
# Comparator paths must remain beneath --root; copy the generated receipt into the ignored local area.
d["baseline"]=[".engineer/test-grade.json"]
d["candidate"]=[".engineer/test-grade.json"]
json.dump(d, open(target, "w", encoding="utf-8"), indent=2)
PY
mkdir -p .engineer
cp "$TMP/grade.json" .engineer/test-grade.json
cp "$TMP/comparison.json" .engineer/test-comparison.json
trap 'rm -rf "$TMP"; rm -f .engineer/test-grade.json .engineer/test-comparison.json' EXIT
python3 "$COMPARATOR" .engineer/test-comparison.json --root "$ROOT" --output "$TMP/report.json"
report_before="$(shasum -a 256 "$TMP/report.json" | cut -d' ' -f1)"
if python3 "$COMPARATOR" .engineer/test-comparison.json --root "$ROOT" --output "$TMP/report.json" >/dev/null 2>&1; then
  echo "expected existing comparison output rejection" >&2
  exit 1
fi
report_after="$(shasum -a 256 "$TMP/report.json" | cut -d' ' -f1)"
test "$report_before" = "$report_after"
ln -s "$ROOT/.engineer/test-comparison.json" "$TMP/comparison-link.json"
if python3 "$COMPARATOR" "$TMP/comparison-link.json" --root "$ROOT" --output "$TMP/symlink-report.json" >/dev/null 2>&1; then
  echo "expected symlinked comparison plan rejection" >&2
  exit 1
fi
python3 "$COMPARISON_VALIDATOR" "$TMP/report.json" --root "$ROOT" >/dev/null
python3 - "$TMP/report.json" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding="utf-8"))
assert d["promotion"]["eligible"] is False
assert d["gate_results"]["distinct_variants"] is False
assert d["metrics"]["candidate_pass_rate"] == 1
PY
python3 - "$TMP/report.json" "$TMP/tampered-report.json" <<'PY'
import json, sys
d=json.load(open(sys.argv[1], encoding="utf-8")); d["promotion"]["eligible"] = True
json.dump(d, open(sys.argv[2], "w", encoding="utf-8"), indent=2)
PY
if python3 "$COMPARISON_VALIDATOR" "$TMP/tampered-report.json" --root "$ROOT" >/dev/null 2>&1; then
  echo "expected tampered comparison rejection" >&2
  exit 1
fi

echo "skill eval deterministic grading fixtures passed"
