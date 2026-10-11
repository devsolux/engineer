#!/usr/bin/env python3
"""Install the complete Engineer command catalog using each host's native format."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

from command_aliases import RECEIPT, digest, plan_host, roots_for, selected_hosts


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosts", help="auto (default), all, or comma-separated hosts")
    parser.add_argument("--project", action="store_true", help="install in the current project (requires --hosts)")
    parser.add_argument("--home", type=Path, help="isolated user home, ignoring profile overrides")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true", help="remove unchanged receipt-owned aliases; preserve native skills")
    parser.add_argument("--check", action="store_true", help="read-only; fail if aliases need installation or refresh")
    args = parser.parse_args()
    if args.project and not args.hosts:
        parser.error("--project requires explicit --hosts")
    home = args.home.expanduser().absolute() if args.home else None
    project = Path.cwd() if args.project else None
    source = Path(__file__).resolve().parent.parent
    try:
        value = args.hosts or "auto"
        hosts = selected_hosts(value, home, project)
        if not hosts:
            raise ValueError("no command host detected; select --hosts explicitly")
        roots = roots_for(home, project)
        # Fail on any conflict before changing any host.
        plans = [plan_host(host, roots[host], source, uninstall=args.uninstall) for host in hosts]
        pending = any(plan["actions"] for plan in plans)
        for plan in plans:
            host = plan["host"]
            status = ("removal pending" if args.uninstall else "pending") if plan["actions"] else ("absent" if args.uninstall else "current")
            spelling = "/prompts:engineer-audit" if host == "codex" else "/engineer-audit"
            print(f"[{host}] {status}: {plan['count']} commands at {plan['destination']}; e.g. {spelling}")
            if not args.dry_run and not args.check:
                for kind, path, data in plan["actions"]:
                    if kind == "link":
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.symlink_to(data, target_is_directory=True)
                    elif kind == "remove":
                        if path.is_symlink() or (host == "hermes" and path.name != RECEIPT and path.parent.is_symlink()):
                            raise ValueError(f"alias changed after preflight: {path}")
                        if digest(path.read_bytes()) != data:
                            raise ValueError(f"alias changed after preflight: {path}")
                        path.unlink()
                        if host == "hermes" and path.name == "SKILL.md":
                            try:
                                path.parent.rmdir()
                            except OSError:
                                pass  # Keep directories containing unrelated files.
                    else:
                        atomic_write(path, data)
        if "codex" in hosts and not args.uninstall:
            print("Codex requires /prompts:engineer-* (deprecated custom-prompt interface); bare /engineer-* is unsupported.")
        if not args.check:
            print("Refresh command catalogs or start new sessions after changes.")
        return 1 if args.check and pending else 0
    except (OSError, ValueError) as exc:
        print(f"alias installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
