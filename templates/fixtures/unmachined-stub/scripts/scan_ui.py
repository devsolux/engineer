#!/usr/bin/env python3
import pathlib
import sys

target = pathlib.Path(sys.argv[-1])
text = target.read_text(encoding="utf-8") if target.is_file() else "".join(
    item.read_text(encoding="utf-8") for item in target.rglob("*") if item.is_file()
)
raise SystemExit(1 if "UI_BLOCK" in text else 0)
