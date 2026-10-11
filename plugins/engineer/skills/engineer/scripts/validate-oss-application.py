#!/usr/bin/env python3
"""Replay an OSS baseline application receipt against templates and target state."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file
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
HEX = set("0123456789abcdef")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def unsafe_path(root: Path, relative: str) -> bool:
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def meaningful_regular(path: Path) -> bool:
    return not path.is_symlink() and path.is_file() and path.stat().st_size > 0


def canonical_files(root: Path, template_root: Path) -> tuple[dict[str, bytes], list[str]]:
    files = {relative: (template_root / name).read_bytes() for relative, name in BASE_FILES.items()}
    ecosystems, scan_limits = detect_dependencies(root)
    if ecosystems and alternate_policy(root) is None:
        files[".github/dependabot.yml"] = render_dependabot(ecosystems)
    return files, scan_limits


def expected_decisions(root: Path) -> list[dict[str, str]]:
    decisions = [{"path": p, "reason": r} for p, r in DECISION_FILES.items() if not meaningful_regular(root / p)]
    if not meaningful_regular(root / "README.md"):
        decisions.append({"path": "README.md", "reason": "document the actual project purpose, status, install, compatibility, support and security links"})
    if not meaningful_regular(root / "GOVERNANCE.md"):
        decisions.append({"path": "GOVERNANCE.md", "reason": "add only when project maturity and decision/release/succession roles require it"})
    updater = alternate_policy(root)
    if updater:
        decisions.append({"path": updater, "reason": "review the project-owned dependency updater policy; do not create a competing Dependabot configuration"})
    return decisions


def validate(data: Any, root: Path, template_root: Path) -> list[str]:
    errors: list[str] = []
    keys = {"schema_version", "mode", "visibility", "root", "operations", "template_set_sha256", "project_decisions_required", "external_mutations", "conflicts", "decision", "limitations"}
    if not isinstance(data, dict) or set(data) != keys:
        return ["receipt must contain exactly the schema-v2 keys"]
    if data["schema_version"] != 2:
        errors.append("schema_version must be 2")
    if not isinstance(data["mode"], str) or data["mode"] not in {"plan", "apply"}:
        errors.append("mode must be plan or apply")
    if data["visibility"] != "public" or data["root"] != ".":
        errors.append("receipt must bind confirmed public visibility and root '.'")
    if data["external_mutations"] != []:
        errors.append("external_mutations must remain empty")
    files, scan_limits = canonical_files(root, template_root)
    if data["limitations"] != LIMITATIONS + scan_limits:
        errors.append("limitations drift from the canonical boundary or dependency scan")
    operations = data["operations"]
    if not isinstance(operations, list) or len(operations) != len(files):
        errors.append("operations must exactly cover the canonical template set")
        operations = []
    expected_set: list[dict[str, str]] = []
    observed_conflicts: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(operations):
        if not isinstance(item, dict) or set(item) != {"path", "template_sha256", "observed_sha256", "status"}:
            errors.append(f"operations[{index}] has invalid keys")
            continue
        relative = item["path"]
        if not isinstance(relative, str) or relative not in files or relative in seen:
            errors.append(f"operations[{index}].path is unexpected, duplicate, or unsafe")
            continue
        seen.add(relative)
        template_sha = sha(files[relative])
        expected_set.append({"path": relative, "template_sha256": template_sha})
        if item["template_sha256"] != template_sha or not is_hash(item["template_sha256"]):
            errors.append(f"operations[{index}].template_sha256 mismatch")
        target = root / relative
        symlinked = unsafe_path(root, relative)
        actual_sha = sha(target.read_bytes()) if not symlinked and target.is_file() else None
        if item["observed_sha256"] != actual_sha:
            errors.append(f"operations[{index}].observed_sha256 does not match target state")
        expected_status = "blocked_symlink" if symlinked else ("present_canonical" if actual_sha == template_sha else ("existing_conflict" if target.exists() else "planned_create"))
        if item["status"] != expected_status:
            errors.append(f"operations[{index}].status is not supported by current state")
        if item["status"] in {"existing_conflict", "blocked_symlink"}:
            observed_conflicts.append(relative)
        if data["mode"] == "apply" and item["status"] == "planned_create":
            errors.append(f"operations[{index}] apply receipt cannot leave a planned creation")

    set_sha = sha(json.dumps(expected_set, sort_keys=True, separators=(",", ":")).encode())
    if data["template_set_sha256"] != set_sha or not is_hash(data["template_set_sha256"]):
        errors.append("template_set_sha256 mismatch")
    if data["conflicts"] != observed_conflicts:
        errors.append("conflicts do not match operation states")
    decisions = expected_decisions(root)
    if data["project_decisions_required"] != decisions:
        errors.append("project_decisions_required does not match target state")
    expected_decision = "review_conflicts" if observed_conflicts else ("review_project_decisions" if decisions else "review_external_settings")
    if data["decision"] != expected_decision:
        errors.append("decision is not derived from conflicts and project decisions")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    receipt = regular_input_file(args.receipt)
    if not root.is_dir() or receipt is None:
        parser.error("receipt must be a regular file, not a symlink, and root must be a directory")
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"invalid OSS application receipt: {exc}")
        return 2
    template_root = Path(__file__).resolve().parent.parent / "templates/github/oss"
    errors = validate(data, root, template_root)
    if args.json:
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
    elif errors:
        print("OSS application receipt invalid:\n" + "\n".join(f"- {error}" for error in errors))
    else:
        print("OSS application receipt valid")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
