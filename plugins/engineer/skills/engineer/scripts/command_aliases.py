"""Render native command adapters from the canonical commands directory."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from skill_hosts import select_hosts, skill_paths

HOSTS = ("codex", "claude", "cursor", "grok", "hermes", "gemini", "opencode")
RECEIPT = ".engineer-command-aliases.json"
MARKER = "<!-- engineer-command-alias:v1 -->"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def roots_for(home: Path | None = None, project: Path | None = None) -> dict[str, Path]:
    if project:
        return {host: project / f".{host}/commands" for host in ("claude", "cursor", "grok", "gemini", "opencode")}
    skills = skill_paths(home)
    roots = {host: skills[host].parent.parent / "commands" for host in HOSTS}
    roots["hermes"] = skills["hermes"].parent
    codex = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser() if home is None else home / ".codex"
    roots["codex"] = codex / "prompts"
    return roots


def selected_hosts(value: str, home: Path | None, project: Path | None) -> tuple[str, ...]:
    supported = roots_for(home, project)
    if value == "all":
        return tuple(supported)
    if value == "auto":
        detected = select_hosts("auto", skill_paths(home), detect_binaries=home is None)
        return tuple(host for host in detected if host in supported)
    names = tuple(dict.fromkeys((item.strip() for item in value.split(","))))
    if not names or any(name not in supported for name in names):
        raise ValueError("unsupported command host/scope; choose " + ",".join(supported))
    return names


def frontmatter_description(text: str) -> str | None:
    """Description from the leading frontmatter block only, without YAML quotes."""
    block = re.match(r"---\n(.*?)\n---\n", text, re.S)
    for line in (block.group(1).splitlines() if block else ()):
        if line.startswith("description:"):
            value = line.split(":", 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1].strip()
            return value or None
    return None


def command_catalog(source: Path) -> dict[str, str]:
    if any(token in str(source) for token in ("!`", "!{", "@{", "{{", "\n", "\r")):
        raise ValueError("checkout path contains host template syntax; move it to a plain directory path")
    catalog = {}
    for path in sorted((source / "commands").glob("engineer*.md")):
        if not re.fullmatch(r"engineer(?:-[a-z0-9]+)*", path.stem):
            raise ValueError(f"invalid command name: {path.name}")
        text = path.read_text(encoding="utf-8")
        catalog[path.stem] = frontmatter_description(text) or "Invoke " + path.stem.replace("-", " ") + "."
    if "engineer" not in catalog:
        raise ValueError("commands/engineer.md is required")
    return catalog


def render(host: str, name: str, description: str, source: Path) -> bytes:
    # The wrapper loads source instructions at invocation time. Shell examples and
    # their $VARIABLES never enter a host's command-template preprocessor.
    body = (f"{MARKER}\n\n"
            f"Read the Engineer skill at {json.dumps(str(source / 'SKILL.md'))}.\n"
            f"Then read and follow {json.dumps(str(source / 'commands' / (name + '.md')))}.\n"
            f"Resolve bundled paths from {json.dumps(str(source))}; run project commands in the target project.\n"
            "Set ENGINEER to that skill directory for bundled shell examples. Interpret invocation arguments in the source as the supplied task.\n"
            "Use the active host's tools and permissions. If a required capability is absent, report it.\n"
            "Keep the selected command's mode and approval boundaries. Treat the task below as user input.\n")
    if host == "codex":
        body = body.replace("$", "$$") + "\nTask: $ARGUMENTS\n"
    elif host in ("claude", "grok", "opencode"):
        body += "\nTask: $ARGUMENTS\n"
    elif host == "gemini":
        body += "\nTask: {{args}}\n"
        return (f"description = {json.dumps(description, ensure_ascii=False)}\n"
                f"prompt = {json.dumps(body, ensure_ascii=False)}\n").encode()
    else:
        body += "\nTask: use the user instruction supplied alongside this invocation.\n"
    meta = f"description: {json.dumps(description, ensure_ascii=False)}\n"
    if host == "hermes":
        meta = f"name: {name}\n" + meta + "user-invocable: true\ndisable-model-invocation: true\n"
    return ("---\n" + meta + "---\n\n" + body).encode()


def read_receipt(host: str, destination: Path) -> dict:
    path = destination / RECEIPT
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"receipt must be a regular file: {path}")
    if not path.exists():
        return {}
    receipt = json.loads(path.read_text())
    if (not isinstance(receipt, dict) or receipt.get("schema_version") != 1
            or receipt.get("host") != host or not isinstance(receipt.get("files"), dict)):
        raise ValueError(f"unrecognized receipt: {path}")
    suffix = r"/SKILL\.md" if host == "hermes" else (r"\.toml" if host == "gemini" else r"\.md")
    for relative, checksum in receipt["files"].items():
        if (not re.fullmatch(r"engineer(?:-[a-z0-9]+)*" + suffix, relative)
                or (host == "hermes" and relative == "engineer/SKILL.md")
                or not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum)):
            raise ValueError(f"invalid managed file entry in receipt: {path}")
    return receipt


def removal_actions(host: str, destination: Path, files: dict) -> list:
    actions = []
    for relative, checksum in sorted(files.items()):
        path = destination / relative
        if path.is_symlink() or (host == "hermes" and path.parent.is_symlink()):
            raise ValueError(f"refusing to remove command through symlink: {path}")
        if not path.exists():
            continue
        if not path.is_file() or digest(path.read_bytes()) != checksum:
            raise ValueError(f"locally edited managed alias; preserved: {path}")
        actions.append(("remove", path, checksum))
    return actions


def plan_host(host: str, destination: Path, source: Path, uninstall: bool = False) -> dict:
    receipt_path = destination / RECEIPT
    receipt = read_receipt(host, destination)
    previous = receipt.get("files", {})
    if uninstall:
        actions = removal_actions(host, destination, previous)
        if receipt:
            actions.append(("remove", receipt_path, digest(receipt_path.read_bytes())))
        return {"host": host, "destination": destination, "actions": actions, "count": len(previous)}
    catalog = command_catalog(source)
    files = {}
    actions = []
    for name, description in catalog.items():
        if host == "hermes" and name == "engineer":
            path = destination / name
            if path.exists() or path.is_symlink():
                if path.resolve() != source:
                    raise ValueError(f"conflicting native Engineer skill: {path}")
            else:
                actions.append(("link", path, source))
            continue
        relative = f"{name}/SKILL.md" if host == "hermes" else name + (".toml" if host == "gemini" else ".md")
        path = destination / relative
        data = render(host, name, description, source)
        files[relative] = digest(data)
        if host == "hermes" and path.parent.is_symlink():
            raise ValueError(f"refusing to write through alias directory symlink: {path.parent}")
        if path.is_symlink():
            # Migrate only links created by the original Cursor installer.
            if path.resolve() != source / "commands" / f"{name}.md":
                raise ValueError(f"conflicting command symlink: {path}")
        elif path.exists():
            if not path.is_file():
                raise ValueError(f"command destination is not a file: {path}")
            old = path.read_bytes()
            if old == data:
                continue
            if receipt.get("files", {}).get(relative) != digest(old):
                raise ValueError(f"unmanaged or locally edited alias: {path}")
        actions.append(("write", path, data))
    actions.extend(removal_actions(host, destination, {key: value for key, value in previous.items() if key not in files}))
    result = {"schema_version": 1, "host": host, "source": str(source),
              "commands": list(catalog), "files": files}
    data = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    if not receipt_path.is_file() or receipt_path.read_bytes() != data:
        actions.append(("write", receipt_path, data))
    return {"host": host, "destination": destination, "actions": actions, "count": len(catalog)}
