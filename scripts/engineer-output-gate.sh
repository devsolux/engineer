#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: engineer-output-gate.sh [--threshold N] [--ui path] file..." >&2
}

THRESHOLD="${UNMACHINED_THRESHOLD:-40}"
UI_TARGET=""
FILES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --threshold)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      THRESHOLD="$2"; shift ;;
    --ui)
      [[ $# -ge 2 ]] || { usage; exit 2; }
      UI_TARGET="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
    *) FILES+=("$1") ;;
  esac
  shift
done

if [[ ! "$THRESHOLD" =~ ^[0-9]+$ ]]; then
  echo "threshold must be a non-negative integer" >&2; exit 2
fi
if [[ ${#FILES[@]} -eq 0 && -z "$UI_TARGET" ]]; then
  usage; exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CANDIDATES=(
  "${UNMACHINED_ROOT:-}"
  "$ROOT/../unmachined"
  "$HOME/.codex/skills/unmachined"
  "$HOME/.claude/skills/unmachined"
)
UNMACHINED=""
for candidate in "${CANDIDATES[@]}"; do
  if [[ -n "$candidate" && -f "$candidate/scripts/scan_text.py" ]]; then
    UNMACHINED="$candidate"; break
  fi
done
if [[ -z "$UNMACHINED" ]]; then
  echo "unmachined scanner unavailable; install it or set UNMACHINED_ROOT" >&2
  exit 3
fi

for file in "${FILES[@]}"; do
  [[ -f "$file" ]] || { echo "missing text target: $file" >&2; exit 2; }
  python3 "$UNMACHINED/scripts/scan_text.py" --threshold "$THRESHOLD" "$file"
  python3 "$UNMACHINED/scripts/scan_text.py" --threshold "$THRESHOLD" --json "$file" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); raise SystemExit(1 if any(x.get("severity") == "critical" for x in d.get("findings", [])) else 0)' \
    || { echo "critical anti-slop finding blocks ship: $file" >&2; exit 1; }
done
if [[ -n "$UI_TARGET" ]]; then
  [[ -d "$UI_TARGET" || -f "$UI_TARGET" ]] || { echo "missing UI target: $UI_TARGET" >&2; exit 2; }
  python3 "$UNMACHINED/scripts/scan_ui.py" --threshold "$THRESHOLD" "$UI_TARGET"
fi
