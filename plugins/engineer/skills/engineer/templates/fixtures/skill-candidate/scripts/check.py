#!/usr/bin/env python3
"""Print the headings in a local Markdown file."""

from pathlib import Path
import sys

path = Path(sys.argv[1]).resolve()
if path.suffix.lower() != ".md" or not path.is_file():
    raise SystemExit("expected a Markdown file")

for line in path.read_text(encoding="utf-8").splitlines():
    if line.startswith("#"):
        print(line)
