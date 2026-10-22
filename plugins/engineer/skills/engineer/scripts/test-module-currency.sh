#!/usr/bin/env bash
# Offline fixtures for scripts/report-module-currency.py: past-due, current, missing header, bad date.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
R="$ROOT/scripts/report-module-currency.py"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/references/nested"
printf '# Current\n\n**Last verified**: 2026-10-01 · **Review cadence**: 3 months\n\nbody\n' > "$T/references/current.md"
printf '# Past due\n\n**Last verified**: 2026-03-01 · **Review cadence**: 3 months\n\nbody\n' > "$T/references/past-due.md"
printf '# Monthly\n\n**Last verified**: 2026-09-01 · **Review cadence**: monthly\n\nbody\n' > "$T/references/nested/monthly.md"
printf '# No header\n\nbody without a currency line\n' > "$T/references/missing.md"
printf '# Bad date\n\n**Last verified**: 2026-13-45 · **Review cadence**: 3 months\n' > "$T/references/bad-date.md"
printf '# No cadence\n\n**Last verified**: 2026-10-01\n' > "$T/references/no-cadence.md"
printf '# Manifest\n\nexcluded by name\n' > "$T/references/MANIFEST.md"
python3 "$R" --root "$T" --today 2026-10-22 --json > "$T/report.json"
python3 - "$T/report.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["modules"]==6, d["modules"]
c=d["counts"]
assert c=={"current":1,"past_due":2,"missing_cadence":1,"missing_header":1,"bad_date":1}, c
by={r["module"]:r for r in d["records"]}
assert by["references/past-due.md"]["overdue_days"]==145, by["references/past-due.md"]
assert by["references/nested/monthly.md"]["status"]=="past_due", by["references/nested/monthly.md"]
assert by["references/current.md"]["due"]=="2026-12-30", by["references/current.md"]
assert d["failing"]==[]
PY
# Informational by default: exit 0 even with past-due modules.
python3 "$R" --root "$T" --today 2026-10-22 >/dev/null
python3 "$R" --root "$T" --today 2026-10-22 --summary | grep -q '^2 past due, 1 without header, 1 without cadence, 1 unparsable, of 6$'
# Gate mode: missing/bad headers and modules overdue beyond the allowance fail.
if python3 "$R" --root "$T" --today 2026-10-22 --fail-after-days 30 >/dev/null; then echo "expected failure with --fail-after-days 30" >&2; exit 1; fi
(python3 "$R" --root "$T" --today 2026-10-22 --fail-after-days 30 --json || true) | python3 -c '
import json,sys; d=json.load(sys.stdin); f=set(d["failing"])
assert f=={"references/past-due.md","references/missing.md","references/bad-date.md","references/no-cadence.md"}, f'
# A symlinked module is skipped rather than followed.
ln -s "$T/references/current.md" "$T/references/link.md"
python3 "$R" --root "$T" --today 2026-10-22 --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["modules"]==6, d["modules"]'
# Missing scope directory is an explicit error.
if python3 "$R" --root "$T" --scope nope --today 2026-10-22 >/dev/null 2>&1; then echo "expected error for missing scope" >&2; exit 1; fi
echo "module currency fixtures passed"
