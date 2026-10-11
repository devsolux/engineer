#!/usr/bin/env bash
# Verify public tables in migrations have RLS enabled (same or later migration)
set -euo pipefail

MIGRATIONS_DIR="${1:-supabase/migrations}"

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
  echo "No migrations dir — skip"
  exit 0
fi

FAIL=0
TABLES=()
RLS_ENABLED=()

while IFS= read -r file; do
  while IFS= read -r table; do
    [[ -z "$table" ]] && continue
    TABLES+=("$table")
  done < <(grep -oiE 'create table (if not exists )?(public\.)?[a-z_][a-z0-9_]*' "$file" \
    | sed -E 's/.*\.//;s/create table (if not exists )?//i' | tr '[:upper:]' '[:lower:]' || true)

  while IFS= read -r table; do
    [[ -z "$table" ]] && continue
    RLS_ENABLED+=("$table")
  done < <(grep -oiE 'alter table (if exists )?(public\.)?[a-z_][a-z0-9_]* enable row level security' "$file" \
    | sed -E 's/.*\.//;s/alter table (if exists )?//i;s/ enable row level security//i' | tr '[:upper:]' '[:lower:]' || true)
done < <(find "$MIGRATIONS_DIR" -name '*.sql' | sort)

# Deduplicate
check_table() {
  local t="$1"
  local found_rls=0
  for r in "${RLS_ENABLED[@]}"; do
    [[ "$r" == "$t" ]] && found_rls=1 && break
  done
  if [[ "$found_rls" -eq 0 ]]; then
    echo "FAIL: public.$t created but no ENABLE ROW LEVEL SECURITY found in migrations"
    FAIL=1
  fi
}

seen=""
for t in "${TABLES[@]}"; do
  [[ "$seen" == *"|$t|"* ]] && continue
  seen="${seen}|$t|"
  check_table "$t"
done

if [[ "$FAIL" -eq 1 ]]; then
  echo ""
  echo "Add to same migration or follow-up:"
  echo "  alter table public.<table> enable row level security;"
  exit 1
fi

echo "RLS migration check passed (${#TABLES[@]} tables)"
exit 0
