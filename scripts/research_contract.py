#!/usr/bin/env python3
"""Shared filesystem and configuration contracts for deep-research tools."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

try:
    import yaml  # supply-chain:allow - standard research dependency
except ImportError:
    yaml = None


class ResearchContractError(ValueError):
    """Raised when a research artifact violates the local trust boundary."""


def load_yaml_or_json(path: Path) -> dict:
    value = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(value) or {}
    else:
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ResearchContractError("PyYAML is required for non-JSON YAML files") from exc
    if not isinstance(loaded, dict):
        raise ResearchContractError(f"{path.name} must contain an object")
    return loaded


def _relative_parts(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value.strip():
        raise ResearchContractError(f"{label} must be a non-empty relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ResearchContractError(f"{label} must be a non-empty relative path without '..'")
    parts = tuple(part for part in pure.parts if part not in ("", "."))
    if not parts:
        raise ResearchContractError(f"{label} must be a strict descendant path")
    return parts


def _reject_symlink_components(root: Path, parts: tuple[str, ...], label: str) -> Path:
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ResearchContractError(f"{label} must not contain symlink components")
    return current


def resolve_relative_path(
    root: Path,
    value: object,
    *,
    label: str,
    kind: str,
    require_exists: bool = True,
) -> Path:
    """Resolve a regular file or directory strictly below root without symlinks."""
    if isinstance(value, Path) and value.is_absolute():
        raise ResearchContractError(f"{label} must be relative")
    if isinstance(value, str) and PurePosixPath(value).is_absolute():
        raise ResearchContractError(f"{label} must be relative")
    return resolve_confined_path(root, value, label=label, kind=kind, require_exists=require_exists)


def resolve_confined_path(
    root: Path,
    value: object,
    *,
    label: str,
    kind: str,
    require_exists: bool = True,
) -> Path:
    """Resolve a relative or already-confined absolute path without losing symlink evidence."""
    root = root.resolve()
    if isinstance(value, Path):
        supplied = value
    elif isinstance(value, str) and value.strip():
        supplied = Path(value)
    else:
        raise ResearchContractError(f"{label} must be a non-empty path")
    if supplied.is_absolute():
        try:
            relative = supplied.relative_to(root)
        except ValueError as exc:
            raise ResearchContractError(f"{label} must remain inside the topic directory") from exc
        parts = _relative_parts(relative.as_posix(), label)
    else:
        parts = _relative_parts(supplied.as_posix(), label)
    raw = _reject_symlink_components(root, parts, label)
    resolved = raw.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ResearchContractError(f"{label} must remain inside the topic directory") from exc
    if require_exists:
        valid = resolved.is_file() if kind == "file" else resolved.is_dir()
        if not valid:
            raise ResearchContractError(f"{label} must be an existing regular {kind}")
    return resolved


def resolve_results_dir(root: Path, outline: dict) -> Path:
    execution = outline.get("execution")
    output_dir = execution.get("output_dir", "./results") if isinstance(execution, dict) else "./results"
    return resolve_relative_path(root, output_dir, label="execution.output_dir", kind="directory")


def resolve_regular_file(root: Path, value: object, *, label: str) -> Path:
    return resolve_relative_path(root, value, label=label, kind="file")


def resolve_confined_file(root: Path, value: object, *, label: str, require_exists: bool = True) -> Path:
    return resolve_confined_path(root, value, label=label, kind="file", require_exists=require_exists)
