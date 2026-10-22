#!/usr/bin/env python3
"""Report reference modules whose own review cadence has lapsed.

Every module under references/ carries a header such as
``**Last verified**: 2026-10-22 · **Review cadence**: 3 months``. This report
derives the due date from those two fields and lists modules that are past due,
missing a header, or missing a cadence. It never rewrites a date: a lapsed module
is re-verified against primary sources or recorded as past-due in the dated
verification ledger (see docs/releasing.md).

The default exit code is 0 so `make check` stays informational; `--fail-after-days N`
turns modules overdue by more than N days into a failure for stricter gates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

VERIFIED = re.compile(r"Last verified\*{0,2}:?\*{0,2}\s*(\d{4}-\d{2}-\d{2})")
CADENCE = re.compile(r"Review cadence\*{0,2}:?\*{0,2}\s*(?:(\d+)\s*(month|week|day)s?|(monthly|weekly|daily))", re.I)
HEADER_LINES = 12
DAYS = {"month": 30, "week": 7, "day": 1, "monthly": 30, "weekly": 7, "daily": 1}
EXCLUDED = {"MANIFEST.md"}


def module_paths(root: Path, scope: str) -> list[Path]:
    base = root / scope
    return sorted(p for p in base.rglob("*.md") if p.name not in EXCLUDED and p.is_file() and not p.is_symlink())


def inspect(path: Path, today: dt.date) -> dict:
    head = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:HEADER_LINES])
    record = {"module": path.as_posix(), "last_verified": None, "cadence_days": None, "due": None, "overdue_days": None, "status": "missing_header"}
    verified = VERIFIED.search(head)
    if not verified:
        return record
    try:
        last = dt.date.fromisoformat(verified.group(1))
    except ValueError:
        record["status"] = "bad_date"
        return record
    record["last_verified"] = last.isoformat()
    cadence = CADENCE.search(head)
    if not cadence:
        record["status"] = "missing_cadence"
        return record
    if cadence.group(3):
        days = DAYS[cadence.group(3).lower()]
    else:
        days = int(cadence.group(1)) * DAYS[cadence.group(2).lower()]
    due = last + dt.timedelta(days=days)
    record.update({"cadence_days": days, "due": due.isoformat(), "overdue_days": max(0, (today - due).days)})
    record["status"] = "past_due" if today > due else "current"
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="repository root")
    ap.add_argument("--scope", default="references", help="directory under the root to scan (default: references)")
    ap.add_argument("--today", default=None, help="override today's date (YYYY-MM-DD) for deterministic runs")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--summary", action="store_true", help="print one summary line only")
    ap.add_argument("--fail-after-days", type=int, default=None, metavar="N",
                    help="exit 1 when any module is overdue by more than N days or lacks a usable header")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    if not (root / args.scope).is_dir():
        print(f"error: {root / args.scope} is not a directory", file=sys.stderr)
        return 2
    records = [inspect(p, today) for p in module_paths(root, args.scope)]
    for r in records:
        r["module"] = Path(r["module"]).resolve().relative_to(root).as_posix()
    counts = {k: sum(1 for r in records if r["status"] == k) for k in ("current", "past_due", "missing_cadence", "missing_header", "bad_date")}
    past_due = sorted((r for r in records if r["status"] == "past_due"), key=lambda r: -r["overdue_days"])
    failing = []
    if args.fail_after_days is not None:
        failing = [r for r in records if r["status"] in {"missing_header", "bad_date", "missing_cadence"}
                   or (r["status"] == "past_due" and r["overdue_days"] > args.fail_after_days)]
    summary = {"today": today.isoformat(), "scope": args.scope, "modules": len(records), "counts": counts,
               "fail_after_days": args.fail_after_days, "failing": [r["module"] for r in failing], "records": records}
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    elif args.summary:
        print(f"{counts['past_due']} past due, {counts['missing_header']} without header, "
              f"{counts['missing_cadence']} without cadence, {counts['bad_date']} unparsable, of {len(records)}")
    else:
        print(f"module currency as of {today.isoformat()} ({args.scope}): {len(records)} modules, "
              f"{counts['current']} current, {counts['past_due']} past due, {counts['missing_cadence']} without cadence, "
              f"{counts['missing_header']} without header, {counts['bad_date']} with an unparsable date")
        for r in past_due:
            print(f"  past due {r['overdue_days']:>4}d  {r['module']}  (verified {r['last_verified']}, due {r['due']})")
        for r in records:
            if r["status"] in {"missing_header", "missing_cadence", "bad_date"}:
                print(f"  {r['status']:<15}  {r['module']}")
        if failing:
            print(f"FAIL: {len(failing)} module(s) exceed --fail-after-days {args.fail_after_days}")
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
