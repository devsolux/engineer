#!/usr/bin/env python3
"""Offline, evidence-bounded OSS repository baseline audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROFILES = {
    "experimental": ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md"],
    "supported": ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "SUPPORT.md"],
    "critical": ["README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "SUPPORT.md", "GOVERNANCE.md", ".github/CODEOWNERS"],
    "deprecated": ["README.md", "LICENSE", "SECURITY.md"],
}
EXTERNAL = [
    "repository visibility and archive state",
    "effective default/release rulesets and bypass actors",
    "private vulnerability reporting",
    "dependency graph, Dependabot, CodeQL and secret scanning settings",
    "immutable release and artifact-attestation settings",
    "collaborator roles, recovery access and organization 2FA policy",
]


def present(root: Path, relative: str) -> bool:
    path = root / relative
    return path.is_file() and path.stat().st_size > 0


def audit(root: Path, profile: str, visibility: str) -> dict[str, object]:
    required = PROFILES[profile]
    files = {path: present(root, path) for path in required}
    forms_dir = root / ".github/ISSUE_TEMPLATE"
    issue_forms = list(forms_dir.glob("*.y*ml")) if forms_dir.is_dir() else []
    pr_template = any(present(root, path) for path in (".github/pull_request_template.md", "pull_request_template.md", "docs/pull_request_template.md"))
    workflows_dir = root / ".github/workflows"
    workflows = list(workflows_dir.glob("*.y*ml")) if workflows_dir.is_dir() else []
    gaps = [path for path, exists in files.items() if not exists] if visibility == "public" else []
    recommended = {
        "structured_issue_form": bool(issue_forms),
        "pull_request_template": pr_template,
        "dependabot_config": present(root, ".github/dependabot.yml") or present(root, ".github/dependabot.yaml"),
        "ci_workflow": bool(workflows),
    }
    if visibility == "public":
        applicability = "confirmed_public"
        decision = "remediate_local" if gaps else "review_external_settings"
    elif visibility == "private":
        applicability = "private_excluded"
        decision = "not_applicable_private"
    else:
        applicability = "unknown_requires_host_evidence"
        decision = "confirm_visibility"
    return {
        "schema_version": 1,
        "profile": profile,
        "visibility": visibility,
        "applicability": applicability,
        "root": ".",
        "required_files": files,
        "recommended_local_signals": recommended,
        "local_gaps": gaps,
        "external_state": {"status": "unknown_requires_host_evidence", "checks": EXTERNAL},
        "decision": decision,
        "limitations": [
            "local files do not prove repository visibility or effective GitHub settings",
            "presence does not prove policy quality, enforcement, response capacity or maintainer independence",
            "this receipt does not mutate files, settings, access or releases",
            "OSS baselines activate only for confirmed public repositories or explicit user OSS scope",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--profile", choices=sorted(PROFILES), default="supported")
    parser.add_argument("--visibility", choices=("unknown", "public", "private"), default="unknown")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        parser.error("root must be a directory")
    result = audit(root, args.profile, args.visibility)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"oss audit — visibility={args.visibility} profile={args.profile} decision={result['decision']}")
        for path, exists in result["required_files"].items():
            print(f"  {'ok' if exists else 'missing':7} {path}")
        print("  external settings: unknown; query the hosting API before claims or mutation")
    return 1 if args.strict and result["local_gaps"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
