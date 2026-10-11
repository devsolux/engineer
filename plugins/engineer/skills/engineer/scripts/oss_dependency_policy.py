#!/usr/bin/env python3
"""Deterministic, bounded Dependabot policy for the OSS baseline."""
from __future__ import annotations

import os
from pathlib import Path

EXCLUDED_DIRS = {".git", ".hg", ".svn", ".tox", ".venv", "node_modules", "vendor", "target", "dist", "build"}
MAX_DEPTH = 4
MAX_DIRECTORIES = 128
ALTERNATE_POLICIES = (
    ".github/dependabot.yaml",
    "renovate.json",
    "renovate.json5",
    ".renovaterc",
    ".renovaterc.json",
    ".github/renovate.json",
)


def alternate_policy(root: Path) -> str | None:
    """Return a project-owned updater policy that blocks automatic Dependabot creation."""
    for relative in ALTERNATE_POLICIES:
        path = root / relative
        if path.exists() or path.is_symlink():
            return relative
    return None


def _ecosystems(names: set[str]) -> set[str]:
    found: set[str] = set()
    if names & {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}:
        found.add("npm")
    if "uv.lock" in names:
        found.add("uv")
    elif "pyproject.toml" in names or "poetry.lock" in names or "Pipfile" in names or any(n.startswith("requirements") and n.endswith(".txt") for n in names):
        found.add("pip")
    checks = {
        "cargo": {"Cargo.toml"}, "gomod": {"go.mod"}, "bundler": {"Gemfile"},
        "composer": {"composer.json"}, "maven": {"pom.xml"}, "gradle": {"build.gradle", "build.gradle.kts"},
        "nuget": {"packages.config"}, "mix": {"mix.exs"}, "pub": {"pubspec.yaml"},
        "bun": {"bun.lock"}, "deno": {"deno.json", "deno.jsonc"},
        "docker": {"Dockerfile"}, "docker-compose": {"compose.yml", "compose.yaml", "docker-compose.yml", "docker-compose.yaml"},
        "bazel": {"MODULE.bazel", "WORKSPACE", "WORKSPACE.bazel"},
        "conda": {"environment.yml", "environment.yaml"},
        "elm": {"elm.json"}, "gitsubmodule": {".gitmodules"}, "helm": {"Chart.yaml"},
        "julia": {"Project.toml", "JuliaProject.toml"},
        "pre-commit": {".pre-commit-config.yaml", ".pre-commit-config.yml", ".pre-commit.yaml", ".pre-commit.yml"},
        "rust-toolchain": {"rust-toolchain", "rust-toolchain.toml"}, "sbt": {"build.sbt"},
        "swift": {"Package.swift"}, "vcpkg": {"vcpkg.json", "vcpkg-configuration.json"},
    }
    for ecosystem, manifests in checks.items():
        if names & manifests or (ecosystem == "nuget" and any(n.endswith((".csproj", ".fsproj", ".vbproj")) for n in names)):
            found.add(ecosystem)
    if "flake.nix" in names and "flake.lock" in names:
        found.add("nix")
    if "global.json" in names:
        found.add("dotnet-sdk")
    if any(name.endswith(".tofu") for name in names) or "terragrunt.hcl" in names:
        found.add("opentofu")
    if ".terraform.lock.hcl" in names and any(name.endswith(".tf") for name in names):
        found.add("terraform")
    return found


def detect(root: Path) -> tuple[dict[str, list[str]], list[str]]:
    """Return allowlisted ecosystem directories and explicit scan limitations."""
    detected: dict[str, set[str]] = {}
    limitations: list[str] = []
    count = 0
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        path = Path(current)
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        depth = len(relative.parts)
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS and not (path / d).is_symlink())
        if depth >= MAX_DEPTH:
            if dirs:
                limitations.append(f"dependency scan stopped below /{relative.as_posix()} at depth {MAX_DEPTH}")
            dirs[:] = []
        names = {name for name in files if not (path / name).is_symlink()}
        ecosystems = _ecosystems(names)
        if any(name.endswith(".tf") for name in names) and not ({"terraform", "opentofu"} & ecosystems):
            location = "/" if not relative.parts else f"/{relative.as_posix()}"
            limitations.append(f"ambiguous Terraform/OpenTofu .tf ownership at {location}; choose the updater explicitly")
        if relative == Path(".github/workflows") and any(n.endswith((".yml", ".yaml")) for n in names):
            ecosystems.add("github-actions")
        if relative.parts[:1] == (".devcontainer",) and "devcontainer.json" in names:
            ecosystems.add("devcontainers")
        directory = "/" if relative == Path(".") or not relative.parts else f"/{relative.as_posix()}"
        for ecosystem in sorted(ecosystems):
            if count >= MAX_DIRECTORIES:
                limitations.append(f"dependency scan capped at {MAX_DIRECTORIES} ecosystem-directory matches")
                return {key: sorted(value) for key, value in sorted(detected.items())}, sorted(set(limitations))
            # GitHub Actions and devcontainers use their repository-wide conventional locations.
            detected.setdefault(ecosystem, set()).add("/" if ecosystem in {"github-actions", "devcontainers"} else directory)
            count += 1
    return {key: sorted(value) for key, value in sorted(detected.items())}, sorted(set(limitations))


def render_dependabot(ecosystems: dict[str, list[str]]) -> bytes:
    lines = ["version: 2", "updates:"]
    for ecosystem, directories in ecosystems.items():
        lines.append(f'  - package-ecosystem: "{ecosystem}"')
        if len(directories) == 1:
            lines.append(f'    directory: "{directories[0]}"')
        else:
            lines.append("    directories:")
            lines.extend(f'      - "{directory}"' for directory in directories)
        lines.extend(["    schedule:", "      interval: weekly", "    open-pull-requests-limit: 5"])
    return ("\n".join(lines) + "\n").encode()
