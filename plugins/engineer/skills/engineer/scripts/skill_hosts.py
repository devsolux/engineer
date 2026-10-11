"""Native user skill roots shared by installation and provenance checks."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

HOST_PATHS = {
    "cursor": ".cursor/skills/engineer",
    "claude": ".claude/skills/engineer",
    "codex": ".agents/skills/engineer",
    "agents": ".agents/skills/engineer",
    "hermes": ".hermes/skills/engineer",
    "opencode": ".config/opencode/skills/engineer",
    "gemini": ".gemini/skills/engineer",
    "grok": ".grok/skills/engineer",
}


def skill_paths(home: Path | None = None) -> dict[str, Path]:
    """An explicit home is hermetic; otherwise honor supported profile roots."""
    paths = {host: (home or Path.home()) / rel for host, rel in HOST_PATHS.items()}
    if home is None:
        for host, variable in (("hermes", "HERMES_HOME"), ("claude", "CLAUDE_CONFIG_DIR")):
            if os.environ.get(variable):
                paths[host] = Path(os.environ[variable]).expanduser() / "skills/engineer"
        if os.environ.get("XDG_CONFIG_HOME"):
            paths["opencode"] = Path(os.environ["XDG_CONFIG_HOME"]).expanduser() / "opencode/skills/engineer"
    return paths


# One owner for optional routing-rule files, shared by the installer and doctor.
ACTIVATION_FILES = {
    "cursor": (".cursor/rules/engineer-auto.mdc",),
    "claude": (".claude/CLAUDE.md",),
    "codex": (".codex/AGENTS.md",),
    "agents": ("AGENTS.md",),
    "hermes": (".hermes/memories/MEMORY.md",),
    "opencode": (".config/opencode/AGENTS.md",),
    "gemini": (".gemini/GEMINI.md",),
    "grok": (".grok/AGENTS.md",),
}
_PROFILE_ROOTS = {
    "claude": ("CLAUDE_CONFIG_DIR", ".claude"),
    "codex": ("CODEX_HOME", ".codex"),
    "hermes": ("HERMES_HOME", ".hermes"),
    "opencode": ("XDG_CONFIG_HOME", ".config"),
}


def activation_paths(home: Path | None = None) -> dict[str, tuple[Path, ...]]:
    """Routing-rule files per host; an explicit home ignores profile overrides."""
    base = home or Path.home()
    paths = {host: tuple(base / rel for rel in rels) for host, rels in ACTIVATION_FILES.items()}
    if home is None:
        for host, (variable, default) in _PROFILE_ROOTS.items():
            if os.environ.get(variable):
                root = Path(os.environ[variable]).expanduser()
                paths[host] = tuple(root / Path(rel).relative_to(default) for rel in ACTIVATION_FILES[host])
    return paths


# Marketplace installs are copied into versioned host caches, not linked to a checkout.
PLUGIN_CACHE = Path("plugins/cache/devsolux-engineer/engineer")


def _version_key(path: Path) -> tuple[int, ...]:
    parts = path.name.split(".")
    return tuple(int(part) for part in parts) if all(part.isdigit() for part in parts) else (-1,)


def plugin_skill_dirs(home: Path | None = None) -> dict[str, list[Path]]:
    """Installed marketplace copies of the engineer skill, newest version last."""
    base = home or Path.home()
    roots = {"claude": base / ".claude", "codex": base / ".codex"}
    if home is None:
        for host in roots:
            variable = _PROFILE_ROOTS[host][0]
            if os.environ.get(variable):
                roots[host] = Path(os.environ[variable]).expanduser()
    found: dict[str, list[Path]] = {}
    for host, root in roots.items():
        cache = root / PLUGIN_CACHE
        if not cache.is_dir() or cache.is_symlink():
            continue
        skills = [entry / "skills/engineer" for entry in sorted(cache.iterdir(), key=_version_key)
                  if (entry / "skills/engineer/SKILL.md").is_file()]
        if skills:
            found[host] = skills
    return found


def select_hosts(value: str, paths: dict[str, Path], detect_binaries: bool = True) -> tuple[str, ...]:
    if value == "all":
        return tuple(paths)
    if value == "auto":
        binaries = {"cursor": ("cursor", "cursor-agent", "agent"), "agents": ()}
        return tuple(host for host, path in paths.items()
                     if path.parent.parent.is_dir()
                     or (host == "codex" and (path.parents[2] / ".codex").is_dir())
                     or (detect_binaries and any(shutil.which(binary)
                         for binary in binaries.get(host, (host,)))))
    hosts = tuple(dict.fromkeys(part.strip() for part in value.split(",")))
    unknown = set(hosts) - set(paths)
    if unknown:
        raise ValueError("unknown or empty hosts: " + ", ".join(sorted(unknown)))
    return hosts
