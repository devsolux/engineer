#!/usr/bin/env python3
"""Plan or apply safe, non-overwriting OSS repository baseline files."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from oss_dependency_policy import alternate_policy, detect as detect_dependencies, render_dependabot

BASE_FILES = {
    "CONTRIBUTING.md": "CONTRIBUTING.md",
    ".github/ISSUE_TEMPLATE/bug.yml": "bug.yml",
    ".github/ISSUE_TEMPLATE/feature.yml": "feature.yml",
    ".github/ISSUE_TEMPLATE/config.yml": "config.yml",
    ".github/pull_request_template.md": "pull_request_template.md",
}
DECISION_FILES = {
    "LICENSE": "select an OSI/FSF-compatible license; never infer legal permission",
    "SECURITY.md": "provide an accountable private vulnerability-reporting channel and supported-version policy",
    "CODE_OF_CONDUCT.md": "select a code and name an accountable enforcement contact",
    "SUPPORT.md": "define maintained support channels and promises",
}
LIMITATIONS = [
    "only missing deterministic in-repository files are created; existing files are never overwritten",
    "license, security contact, conduct enforcement, support and governance require accountable project decisions",
    "the receipt does not change GitHub settings, access, visibility, releases, packages or vulnerability reporting",
    "effective host state still requires GitHub API evidence",
    "replay verifies final local state but cannot independently prove prior file absence or applicator process identity",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unsafe_path(root: Path, relative: str) -> bool:
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def desired_files(root: Path, template_root: Path) -> tuple[dict[str, bytes], list[str]]:
    files = {relative: (template_root / name).read_bytes() for relative, name in BASE_FILES.items()}
    ecosystems, scan_limits = detect_dependencies(root)
    if ecosystems and alternate_policy(root) is None:
        files[".github/dependabot.yml"] = render_dependabot(ecosystems)
    return files, scan_limits


def template_set_sha256(entries: list[dict[str, object]]) -> str:
    canonical = [{"path": item["path"], "template_sha256": item["template_sha256"]} for item in entries]
    return digest(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode())


def meaningful_regular(path: Path) -> bool:
    return not path.is_symlink() and path.is_file() and path.stat().st_size > 0


def apply(root: Path, template_root: Path, do_apply: bool) -> dict[str, object]:
    operations: list[dict[str, object]] = []
    desired, scan_limits = desired_files(root, template_root)
    for relative, body in desired.items():
        template_sha = digest(body)
        target = root / relative
        if unsafe_path(root, relative):
            status = "blocked_symlink"
            observed_sha = None
        elif target.exists():
            observed_sha = digest(target.read_bytes()) if target.is_file() else None
            status = "present_canonical" if observed_sha == template_sha else "existing_conflict"
        elif do_apply:
            target.parent.mkdir(parents=True, exist_ok=True)
            if unsafe_path(root, relative):
                operations.append({"path": relative, "template_sha256": template_sha, "observed_sha256": None, "status": "blocked_symlink"})
                continue
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(target, flags, 0o644)
            with os.fdopen(fd, "wb") as handle:
                handle.write(body)
            status = "present_canonical"
            observed_sha = template_sha
        else:
            status = "planned_create"
            observed_sha = None
        operations.append({"path": relative, "template_sha256": template_sha, "observed_sha256": observed_sha, "status": status})

    decisions = [
        {"path": path, "reason": reason}
        for path, reason in DECISION_FILES.items()
        if not meaningful_regular(root / path)
    ]
    if not meaningful_regular(root / "README.md"):
        decisions.append({"path": "README.md", "reason": "document the actual project purpose, status, install, compatibility, support and security links"})
    if not meaningful_regular(root / "GOVERNANCE.md"):
        decisions.append({"path": "GOVERNANCE.md", "reason": "add only when project maturity and decision/release/succession roles require it"})
    updater = alternate_policy(root)
    if updater:
        decisions.append({"path": updater, "reason": "review the project-owned dependency updater policy; do not create a competing Dependabot configuration"})

    conflicts = [item["path"] for item in operations if item["status"] in {"existing_conflict", "blocked_symlink"}]
    return {
        "schema_version": 2,
        "mode": "apply" if do_apply else "plan",
        "visibility": "public",
        "root": ".",
        "operations": operations,
        "template_set_sha256": template_set_sha256(operations),
        "project_decisions_required": decisions,
        "external_mutations": [],
        "conflicts": conflicts,
        "decision": "review_conflicts" if conflicts else ("review_project_decisions" if decisions else "review_external_settings"),
        "limitations": LIMITATIONS + scan_limits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--visibility", choices=("public", "private", "unknown"), default="unknown")
    parser.add_argument("--apply", action="store_true", help="create missing safe files atomically")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", type=Path, help="write a new receipt at this target-relative path")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error("root must be a directory")
    if args.visibility != "public":
        parser.error("safe OSS application requires confirmed public visibility")
    template_root = Path(__file__).resolve().parent.parent / "templates/github/oss"
    result = apply(root, template_root, args.apply)
    if args.output:
        if args.output.is_absolute() or ".." in args.output.parts or args.output == Path("."):
            parser.error("output must be a safe target-relative file path")
        output = root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        if unsafe_path(root, args.output.as_posix()) or output.exists():
            parser.error("output path must be new and must not traverse a symlink")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(output, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"oss baseline {result['mode']} — decision={result['decision']}")
        for item in result["operations"]:
            print(f"  {item['status']:18} {item['path']}")
        for item in result["project_decisions_required"]:
            print(f"  decision-required  {item['path']}: {item['reason']}")
    return 2 if result["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
