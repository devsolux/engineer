#!/usr/bin/env python3
"""Scan executable documentation and workflows for floating remote execution."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable

SHELL_LANGS = {"", "bash", "console", "sh", "shell", "zsh"}
REMOTE_PIPE = re.compile(r"(?:curl|wget)\b[^\n|]*\|\s*(?:ba)?sh\b", re.IGNORECASE)
RUNNER = re.compile(r"\b(npx|pnpm\s+dlx|yarn\s+dlx|bunx|uvx)\s+(?:--yes\s+)?([^\s;|&]+)", re.IGNORECASE)
ACTION = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)@([^\s#]+)")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXACT_VERSION = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def exact_runner_spec(runner: str, spec: str) -> bool:
    spec = spec.strip("'\"")
    if runner.lower() == "uvx":
        return "==" in spec and bool(EXACT_VERSION.fullmatch(spec.rsplit("==", 1)[1]))
    if spec.startswith("@"):
        separator = spec.rfind("@")
        version = spec[separator + 1 :] if separator > 0 else ""
    else:
        version = spec.rsplit("@", 1)[1] if "@" in spec else ""
    return bool(EXACT_VERSION.fullmatch(version)) or bool(SHA40.fullmatch(version))


def markdown_shell_lines(path: Path) -> Iterable[tuple[int, str]]:
    inside = False
    scan = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if not inside:
                language = stripped[3:].strip().split(maxsplit=1)[0].lower() if stripped[3:].strip() else ""
                inside = True
                scan = language in SHELL_LANGS
            else:
                inside = False
                scan = False
            continue
        if inside and scan:
            yield number, line


def scan_markdown(path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, line in markdown_shell_lines(path):
        if REMOTE_PIPE.search(line):
            findings.append({"file": str(path), "line": line_number, "rule": "remote-pipe-interpreter", "text": line.strip()})
        for match in RUNNER.finditer(line):
            runner, spec = match.groups()
            if not exact_runner_spec(runner, spec):
                findings.append({"file": str(path), "line": line_number, "rule": "floating-package-runner", "text": line.strip()})
    return findings


def scan_workflow(path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        match = ACTION.match(line)
        if not match:
            continue
        target, revision = match.groups()
        if target.startswith("./"):
            continue
        if not SHA40.fullmatch(revision):
            findings.append({"file": str(path), "line": line_number, "rule": "mutable-action-ref", "text": line.strip()})
        elif not re.search(r"#\s*v?\d", line):
            findings.append({"file": str(path), "line": line_number, "rule": "action-pin-missing-release-comment", "text": line.strip()})
    return findings


def candidates(root: Path, requested: list[str]) -> list[Path]:
    if requested:
        paths = [root / item for item in requested]
    else:
        paths = []
        for base in (root / "SKILL.md", root / "README.md", root / "SECURITY.md", root / "CONTRIBUTING.md"):
            if base.is_file():
                paths.append(base)
        for directory in ("docs", "references", "commands", "templates", ".github/workflows"):
            base = root / directory
            if base.exists():
                paths.extend(p for p in base.rglob("*") if p.suffix.lower() in {".md", ".yml", ".yaml"})
    return sorted({path.resolve() for path in paths if path.is_file()})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path.cwd().resolve()
    findings: list[dict[str, object]] = []
    for path in candidates(root, args.paths):
        try:
            display_path = path.relative_to(root)
        except ValueError:
            display_path = path
        if path.suffix.lower() == ".md":
            current = scan_markdown(path)
        elif path.suffix.lower() in {".yml", ".yaml"}:
            current = scan_workflow(path)
        else:
            current = []
        for finding in current:
            finding["file"] = str(display_path)
        findings.extend(current)
    result = {
        "ok": not findings,
        "findings": findings,
        "scope": "executable Markdown fences and active workflow action references",
        "limitation": "A clean result is not proof that a skill or dependency is benign.",
    }
    if args.json:
        print(json.dumps(result, indent=2))
    elif findings:
        for finding in findings:
            print(f"{finding['file']}:{finding['line']}: {finding['rule']}: {finding['text']}")
    else:
        print("documentation supply-chain scan passed")
        print(result["limitation"])
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
