#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

GRADER="$ROOT/scripts/grade-skill-eval-capture.py"
CAPTURE="$ROOT/templates/agentic/skill-eval-capture.sample.json"
ORACLE="$ROOT/templates/agentic/skill-eval-oracle.sample.json"

python3 "$GRADER" "$CAPTURE" --oracle "$ORACLE" --root "$ROOT" --output "$TMP/grade.json"
before="$(shasum -a 256 "$TMP/grade.json" | cut -d' ' -f1)"
if python3 "$GRADER" "$CAPTURE" --oracle "$ORACLE" --root "$ROOT" --output "$TMP/grade.json" >/dev/null 2>&1; then
  echo "grader overwrote an existing evidence receipt" >&2
  exit 1
fi
after="$(shasum -a 256 "$TMP/grade.json" | cut -d' ' -f1)"
test "$before" = "$after"

printf 'project-owned\n' >"$TMP/victim"
ln -s "$TMP/victim" "$TMP/grade-link.json"
if python3 "$GRADER" "$CAPTURE" --oracle "$ORACLE" --root "$ROOT" --output "$TMP/grade-link.json" >/dev/null 2>&1; then
  echo "grader followed a symlinked output" >&2
  exit 1
fi
grep -q '^project-owned$' "$TMP/victim"

ln -s "$TMP/victim" "$TMP/host-link.json"
if python3 "$ROOT/scripts/capture-host-capabilities.py" --cwd "$ROOT" --output "$TMP/host-link.json" >/dev/null 2>&1; then
  echo "host capability capture followed a symlinked output" >&2
  exit 1
fi
grep -q '^project-owned$' "$TMP/victim"

mkdir "$TMP/mcp-existing"
printf 'project-owned\n' >"$TMP/mcp-existing/sentinel"
if python3 "$ROOT/scripts/compile-mcp-transcript.py" \
  "$ROOT/templates/agentic/mcp-evidence/transcript.jsonl" \
  --output-dir "$TMP/mcp-existing" >/dev/null 2>&1; then
  echo "MCP compiler reused an existing publication directory" >&2
  exit 1
fi
grep -q '^project-owned$' "$TMP/mcp-existing/sentinel"

echo "evidence output boundary fixtures passed"
