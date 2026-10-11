#!/usr/bin/env python3
"""Shared lexical confinement for hash-bound evidence artifacts."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


def is_under(path: Path, root: Path) -> bool:
    """True when path is inside root after resolve.

    APFS can expose the same inode under two casings (e.g. MyApp vs myapp).
    pathlib.relative_to compares strings and fails that case; samefile does not.
    Symlink policy stays on resolve() plus the caller's component walk.
    """
    try:
        path = path.resolve()
        root = root.resolve()
        path.relative_to(root)
        return True
    except (ValueError, OSError):
        pass
    try:
        current = path.resolve()
        root = root.resolve()
        while True:
            if os.path.samefile(current, root):
                return True
            parent = current.parent
            if parent == current:
                return False
            current = parent
    except OSError:
        return False


def relative_posix(path: Path, root: Path) -> str:
    """Repo-relative POSIX path, tolerant of macOS case aliases."""
    path = path.resolve()
    root = root.resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        if not is_under(path, root):
            raise ValueError(f"{path} is not in the subpath of {root}") from None
        parts: list[str] = []
        current = path
        while True:
            if os.path.samefile(current, root):
                break
            parts.append(current.name)
            current = current.parent
        return "/".join(reversed(parts)) or "."


def safe_path(value: Any, root: Path) -> Path | None:
    """Return a confined path only when no supplied component is a symlink."""
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        return None
    if PureWindowsPath(value).drive:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        return None
    root = root.resolve()
    current = root
    for part in pure.parts:
        if part in ("", "."):
            continue
        current = current / part
        if current.is_symlink():
            return None
    resolved = current.resolve()
    if not is_under(resolved, root):
        return None
    return resolved


def regular_input_file(value: Any) -> Path | None:
    """Resolve a CLI input only when its final supplied path is a regular file.

    This preserves the identity of the user-supplied argument long enough to
    reject a final symlink. Paths referenced by an evidence document still
    require ``safe_path`` and its explicit trust root.
    """
    if not isinstance(value, (str, Path)):
        return None
    supplied = Path(value)
    if supplied.is_symlink() or not supplied.is_file():
        return None
    return supplied.resolve()


def create_new_bytes(value: Any, body: bytes, *, mode: int = 0o600) -> Path:
    """Create one immutable artifact without following or replacing its final name."""
    if not isinstance(value, (str, Path)) or not isinstance(body, bytes):
        raise ValueError("output path and byte body required")
    path = Path(value)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    return path.resolve()


def create_new_text(value: Any, body: str, *, mode: int = 0o600) -> Path:
    """UTF-8 wrapper for immutable artifact creation."""
    if not isinstance(body, str):
        raise ValueError("text body required")
    return create_new_bytes(value, body.encode("utf-8"), mode=mode)
