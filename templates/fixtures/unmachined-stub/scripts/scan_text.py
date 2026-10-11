#!/usr/bin/env python3
import pathlib
import json
import sys

target = pathlib.Path(sys.argv[-1])
text = target.read_text(encoding="utf-8")
blocked = "BLOCK_ME" in text
critical_only = "CRITICAL_ONLY" in text
if "--json" in sys.argv:
    print(json.dumps({"score": 100 if blocked else 20 if critical_only else 0, "pass": not blocked, "findings": [{"severity": "critical"}] if blocked or critical_only else []}))
raise SystemExit(1 if blocked else 0)
