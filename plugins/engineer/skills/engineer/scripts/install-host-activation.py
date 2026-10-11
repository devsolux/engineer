#!/usr/bin/env python3
"""Install bounded, idempotent Engineer routing rules for local CLI hosts."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from skill_hosts import ACTIVATION_FILES, activation_paths

BEGIN = "<!-- engineer-auto:begin -->"
END = "<!-- engineer-auto:end -->"
BODY = f"""{BEGIN}
## Engineer automatic routing

For software and product-engineering work, automatically activate the installed
`engineer` skill before planning or using tools, even when the user does not name it.
This includes implementation, debugging, refactoring, architecture, UI, APIs,
security, testing, browser QA, deployment, product analytics, agent engineering,
and technical research. Load only the relevant Engineer modules.

Do not activate Engineer for generic business strategy, pure social content,
mobile-only work, or notebook data science unless the task is explicitly adapted.
If a narrower installed skill has a material advantage, Engineer may compose with it
or defer that domain while retaining engineering verification. Skill activation
does not expand permissions or authorize external actions.
{END}
"""

ALL_HOSTS = tuple(ACTIVATION_FILES)


def strip_block(text: str) -> str:
    start = text.find(BEGIN)
    if start < 0:
        return text
    end = text.find(END, start)
    if end < 0:
        raise ValueError("found Engineer activation start marker without end marker")
    end += len(END)
    return (text[:start].rstrip() + "\n\n" + text[end:].lstrip()).strip() + "\n"


def atomic_write(path: Path, text: str) -> None:
    # Dotfile managers often symlink these files; update the real file, never replace the link.
    if path.is_symlink():
        path = path.resolve(strict=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(text)
        temp = Path(handle.name)
    temp.chmod(mode)
    os.replace(temp, path)


def update_markdown(path: Path, remove: bool) -> str:
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    clean = strip_block(old)
    new = clean if remove else (clean.rstrip() + "\n\n" + BODY)
    if new != old:
        atomic_write(path, new)
        return "removed" if remove else "installed"
    return "current"


def update_cursor(path: Path, remove: bool) -> tuple[Path, str]:
    if remove:
        if path.exists():
            path.unlink()
            return path, "removed"
        return path, "absent"
    content = """---
description: Automatically route matching software and product-engineering work to Engineer
alwaysApply: true
---

""" + BODY
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old != content:
        atomic_write(path, content)
        return path, "installed"
    return path, "current"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosts", default="all")
    parser.add_argument("--home", type=Path, help="explicit home; ignores profile environment overrides")
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    hosts = ALL_HOSTS if args.hosts == "all" else tuple(x.strip() for x in args.hosts.split(",") if x.strip())
    unknown = sorted(set(hosts) - set(ALL_HOSTS))
    if unknown:
        parser.error("unknown hosts: " + ", ".join(unknown))

    paths = activation_paths(args.home.expanduser().absolute() if args.home else None)
    try:
        return apply(hosts, paths, args.remove, args.check)
    except (OSError, ValueError) as exc:
        print(f"activation update failed: {exc}", file=sys.stderr)
        return 1


def apply(hosts: tuple[str, ...], paths: dict[str, tuple[Path, ...]], remove: bool, check: bool) -> int:
    failures = 0
    for host in hosts:
        targets = paths[host]
        if check:
            for path in targets:
                valid = path.is_file() and BEGIN in path.read_text(encoding="utf-8") and END in path.read_text(encoding="utf-8")
                print(f"  [{host}] {'current' if valid else 'missing'} {path}")
                failures += 0 if valid else 1
            continue
        if host == "cursor":
            path, status = update_cursor(targets[0], remove)
            print(f"  [{host}] {status} {path}")
        else:
            for path in targets:
                print(f"  [{host}] {update_markdown(path, remove)} {path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
