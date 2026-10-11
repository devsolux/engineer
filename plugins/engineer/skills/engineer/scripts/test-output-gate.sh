#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GATE="$ROOT/scripts/engineer-output-gate.sh"
STUB="$ROOT/templates/fixtures/unmachined-stub"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

printf '%s\n' 'Concrete product evidence.' > "$TMP/pass.md"
printf '%s\n' 'BLOCK_ME' > "$TMP/fail.md"
printf '%s\n' 'CRITICAL_ONLY' > "$TMP/critical.md"
printf '%s\n' 'export default function Page() { return null }' > "$TMP/pass.tsx"
printf '%s\n' 'UI_BLOCK' > "$TMP/fail.tsx"

UNMACHINED_ROOT="$STUB" bash "$GATE" "$TMP/pass.md"
if UNMACHINED_ROOT="$STUB" bash "$GATE" "$TMP/fail.md" >/dev/null 2>&1; then
  echo "expected text gate failure" >&2; exit 1
fi
if UNMACHINED_ROOT="$STUB" bash "$GATE" "$TMP/critical.md" >/dev/null 2>&1; then
  echo "expected critical finding below threshold to fail" >&2; exit 1
fi
UNMACHINED_ROOT="$STUB" bash "$GATE" --ui "$TMP/pass.tsx" "$TMP/pass.md"
if UNMACHINED_ROOT="$STUB" bash "$GATE" --ui "$TMP/fail.tsx" "$TMP/pass.md" >/dev/null 2>&1; then
  echo "expected UI gate failure" >&2; exit 1
fi
if UNMACHINED_ROOT="$STUB" bash "$GATE" --threshold nope "$TMP/pass.md" >/dev/null 2>&1; then
  echo "expected threshold validation failure" >&2; exit 1
fi
echo "output gate fixtures passed"
