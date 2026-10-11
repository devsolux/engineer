#!/usr/bin/env python3
"""Link one reviewed engineer checkout into selected native skill directories."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from skill_hosts import select_hosts, skill_paths


def link_state(path: Path, source: Path) -> str:
    if path.is_symlink() and path.resolve() == source:
        return "current"
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to replace existing path: {path}; inspect and move it explicitly")
    return "link"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosts", default="auto", help="auto (default), all, or comma-separated host names")
    parser.add_argument("--home", type=Path, help="explicit home; ignores profile environment overrides")
    parser.add_argument("--skills-dir", type=Path, help="custom native skills root; installs only there")
    parser.add_argument("--uninstall", action="store_true", help="remove only native links pointing to this checkout")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pull", action="store_true", help="explicitly git pull --ff-only before linking")
    args = parser.parse_args()
    if args.skills_dir and args.hosts != "auto":
        parser.error("--skills-dir cannot be combined with --hosts")
    if args.uninstall and args.pull:
        parser.error("--uninstall cannot be combined with --pull")
    source = Path(__file__).resolve().parent.parent
    try:
        if not (source / "SKILL.md").is_file():
            raise ValueError("source is missing SKILL.md")
        paths = skill_paths(args.home.expanduser().absolute() if args.home else None)
        if args.skills_dir:
            targets = {"custom": args.skills_dir.expanduser().absolute() / "engineer"}
        else:
            hosts = select_hosts(args.hosts, paths, detect_binaries=args.home is None)
            targets = {host: paths[host] for host in hosts}
        # Preflight every install target before any write, including an optional pull.
        # Uninstall never needs a preflight: it only removes links to this checkout.
        states = {} if args.uninstall else {host: link_state(path, source) for host, path in targets.items()}
        if not targets:
            print("No host detected. Select --hosts or --skills-dir explicitly.")
            return 0
        if args.pull:
            if args.dry_run:
                print("would run git pull --ff-only")
            else:
                subprocess.run(["git", "-C", str(source), "pull", "--ff-only"], check=True)
        for host, path in targets.items():
            if args.uninstall:
                current = path.is_symlink() and path.resolve() == source
                foreign = not current and (path.exists() or path.is_symlink())
                print(f"[{host}] {'unlink' if current else 'skip (not linked to this checkout)' if foreign else 'absent'} {path}")
                if current and not args.dry_run:
                    path.unlink()
                continue
            print(f"[{host}] {states[host]} {path} -> {source}")
            if not args.dry_run and link_state(path, source) != "current":
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(source, target_is_directory=True)
        if args.uninstall:
            print("Native links removed. Command aliases are managed separately by install-commands.sh --uninstall.")
            return 0
        print("Native skill only. Refresh the host skill catalog or start a new session.")
        if "codex" in targets or "agents" in targets:
            print("Codex: $engineer audit <target>. Optional aliases: scripts/install-commands.sh --hosts codex (/prompts:engineer-*).")
        if "claude" in targets:
            print("Claude Code: /engineer audit <target>")
        if "cursor" in targets:
            print("Cursor: select engineer, or install /engineer-* aliases separately with scripts/install-commands.sh --hosts cursor.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"install failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
