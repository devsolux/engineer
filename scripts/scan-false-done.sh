#!/usr/bin/env bash
# engineer false-done scanner — catch the failure modes behind agents claiming
# "done" against only the checks they can see: skipped/focused tests, explicit
# not-implemented markers, mocks/stubs/placeholders in production paths, and
# test files edited inside a feature changeset (a self-certification vector).
#
# Deterministic enforcement of references/implementation-completeness.md. Run in
# the TARGET app repo, on the changeset, before reporting done.
#
# Usage: scan-false-done.sh [--base <ref>] [--staged] [--strict] [--json] [--quiet]
#   default: diff the working tree + index against HEAD
#   --base <ref>: diff against <ref> (e.g. origin/main, or a merge-base)
#   --staged:     diff only staged changes (index vs HEAD)
#   --strict:     warnings also fail (exit 1); default fails only on BLOCK
#   --json:       machine-readable findings
#   --quiet:      suppress the passing/among lines, print findings only
#
# Exit: 0 clean (or warnings-only without --strict); 1 warnings under --strict;
#       2 BLOCK-level findings; 3 not a git repo / bad invocation.
set -euo pipefail

BASE=""
STAGED=0
STRICT=0
JSON_OUT=0
QUIET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base) BASE="${2:-}"; shift 2;;
    --staged) STAGED=1; shift;;
    --strict) STRICT=1; shift;;
    --json) JSON_OUT=1; shift;;
    --quiet) QUIET=1; shift;;
    -h|--help)
      sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 3;;
  esac
done

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "scan-false-done: not a git repository (run in the target app repo)" >&2
  exit 3
fi

# Build the diff command.
if [[ -n "$BASE" ]]; then
  DIFF_ARGS=("$BASE")
elif [[ "$STAGED" == "1" ]]; then
  DIFF_ARGS=(--cached)
else
  DIFF_ARGS=(HEAD)
fi

# --- classification patterns -------------------------------------------------
# Note: bash [[ =~ ]] is POSIX ERE — no \b. Word boundaries are emulated with
# (^|[^A-Za-z]) … ([^A-Za-z]|$).
# BLOCK: near-always false-done in a changeset reported as complete.
#   skipped / focused tests (any file)
SKIP_TESTS='(\.only\(|\.skip\(|(^|[^A-Za-z])xit\(|(^|[^A-Za-z])xdescribe\(|(^|[^A-Za-z])fdescribe\(|(^|[^A-Za-z])it\.todo\(|@pytest\.mark\.skip|@unittest\.skip|@Disabled|(^|[^A-Za-z])t\.Skip\()'
#   explicit not-implemented (production files)
NOT_IMPL='(NotImplementedError|raise NotImplemented|throw new Error\(["'"'"']?[Nn]ot implemented|panic!\("not implemented|todo!\(\)|unimplemented!\()'
# WARN: deferral / placeholder signals in production files.
DEFER='(^|[^A-Za-z])(TODO|FIXME|XXX|HACK|stub|mock|placeholder)([^A-Za-z]|$)|for now|coming soon'

is_test_file() {
  [[ "$1" =~ (\.|_)(test|spec)\.[jt]sx?$ ]] && return 0
  [[ "$1" =~ (^|/)test_[^/]*\.py$ ]] && return 0
  [[ "$1" =~ _test\.(py|go)$ ]] && return 0
  [[ "$1" =~ (^|/)(tests?|__tests__)/ ]] && return 0
  return 1
}

BLOCK_FINDINGS=()
WARN_FINDINGS=()
CHANGED_TEST=0
CHANGED_SRC=0

current=""
# Walk the unified diff; only added lines (leading '+', not '+++') are scanned.
while IFS= read -r line; do
  case "$line" in
    "+++ b/"*) current="${line#+++ b/}"; continue;;
    "+++ /dev/null") current=""; continue;;
    "+++ "*) current="${line#+++ }"; continue;;
  esac
  [[ -z "$current" ]] && continue
  # track file classes touched (from the +++ headers we just parsed)
  # (counted once per file below)
  case "$line" in
    "+"*) ;;                       # an added content line
    *) continue;;
  esac
  [[ "$line" == "+++"* ]] && continue
  content="${line:1}"

  testfile=0
  if is_test_file "$current"; then testfile=1; fi

  # skipped/focused tests — BLOCK in any file
  if [[ "$content" =~ $SKIP_TESTS ]]; then
    BLOCK_FINDINGS+=("$current|skipped-or-focused-test|${content:0:120}")
  fi
  # not-implemented — BLOCK in production files only
  if [[ "$testfile" == "0" && "$content" =~ $NOT_IMPL ]]; then
    BLOCK_FINDINGS+=("$current|not-implemented|${content:0:120}")
  fi
  # deferral/placeholder — WARN in production files only
  if [[ "$testfile" == "0" && "$content" =~ $DEFER ]]; then
    WARN_FINDINGS+=("$current|deferral-or-placeholder|${content:0:120}")
  fi
done < <(git diff "${DIFF_ARGS[@]}" --unified=0 2>/dev/null || true)

# Which file classes changed (name-only is cheaper + reliable for the heuristic).
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  if is_test_file "$f"; then CHANGED_TEST=1; else CHANGED_SRC=1; fi
done < <(git diff "${DIFF_ARGS[@]}" --name-only 2>/dev/null || true)

if [[ "$CHANGED_TEST" == "1" && "$CHANGED_SRC" == "1" ]]; then
  WARN_FINDINGS+=("changeset|tests-edited-with-implementation|test files changed alongside implementation — re-verify with a check the writer did not edit")
fi

# --- output ------------------------------------------------------------------
emit_human() {
  local n_block=${#BLOCK_FINDINGS[@]} n_warn=${#WARN_FINDINGS[@]}
  if [[ "$n_block" -gt 0 ]]; then
    echo "BLOCK (false-done): $n_block"
    for f in ${BLOCK_FINDINGS[@]+"${BLOCK_FINDINGS[@]}"}; do
      IFS='|' read -r file kind snip <<<"$f"; echo "  ✗ [$kind] $file: $snip"
    done
  fi
  if [[ "$n_warn" -gt 0 ]]; then
    echo "WARN: $n_warn"
    for f in ${WARN_FINDINGS[@]+"${WARN_FINDINGS[@]}"}; do
      IFS='|' read -r file kind snip <<<"$f"; echo "  ! [$kind] $file: $snip"
    done
  fi
  if [[ "$n_block" -eq 0 && "$n_warn" -eq 0 && "$QUIET" -eq 0 ]]; then
    echo "scan-false-done: clean — no false-done markers in the changeset"
  fi
}

emit_json() {
  printf '{"block":['
  local first=1
  for f in ${BLOCK_FINDINGS[@]+"${BLOCK_FINDINGS[@]}"}; do
    IFS='|' read -r file kind snip <<<"$f"
    [[ $first -eq 0 ]] && printf ','
    printf '{"file":"%s","kind":"%s"}' "$file" "$kind"; first=0
  done
  printf '],"warn":['
  first=1
  for f in ${WARN_FINDINGS[@]+"${WARN_FINDINGS[@]}"}; do
    IFS='|' read -r file kind snip <<<"$f"
    [[ $first -eq 0 ]] && printf ','
    printf '{"file":"%s","kind":"%s"}' "$file" "$kind"; first=0
  done
  printf ']}\n'
}

if [[ "$JSON_OUT" == "1" ]]; then emit_json; else emit_human; fi

if [[ "${#BLOCK_FINDINGS[@]}" -gt 0 ]]; then exit 2; fi
if [[ "$STRICT" == "1" && "${#WARN_FINDINGS[@]}" -gt 0 ]]; then exit 1; fi
exit 0
