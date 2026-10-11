#!/usr/bin/env python3
"""Capture a secret-safe inventory of installed coding-agent host surfaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import create_new_text

HOSTS = {
    "codex": {
        "version_command": ["codex", "--version"],
        "help_commands": [["codex", "--help"], ["codex", "exec", "--help"], ["codex", "plugin", "--help"]],
        "tokens": {
            "non_interactive": "exec", "mcp": "mcp", "mcp_server": "mcp-server",
            "sandbox": "sandbox", "approvals": "ask-for-approval", "resume": "resume",
            "profiles": "profile", "web_search": "--search", "cloud": "cloud",
            "feature_flags": "features", "structured_output": "json",
            "strict_config": "--strict-config", "code_review": "review",
            "plugins": "plugin", "app_server": "app-server", "remote_control": "remote-control",
            "remote_client": "--remote", "session_fork": "fork", "session_archive": "archive",
            "local_provider": "--local-provider", "hooks": "--dangerously-bypass-hook-trust",
            "plugin_marketplace": "marketplace", "feature_toggles": "--enable",
            "exec_server": "exec-server", "profile_as_file": ".config.toml",
        },
    },
    "claude": {
        "version_command": ["claude", "--version"],
        "help_commands": [["claude", "--help"]],
        "tokens": {
            "non_interactive": "--print", "mcp": "mcp", "plugins": "plugin",
            "permission_modes": "--permission-mode", "resume": "--resume",
            "worktrees": "--worktree", "subagents": "--agents", "background_agents": "--background",
            "structured_output": "--json-schema", "streaming_json": "stream-json",
            "browser": "--chrome", "bare_mode": "--bare", "no_persistence": "--no-session-persistence",
            "safe_mode": "--safe-mode", "remote_control": "--remote-control",
            "cloud_review": "ultrareview", "fallback_model": "--fallback-model",
            "effort_control": "--effort", "cost_budget": "--max-budget-usd",
            "strict_mcp": "--strict-mcp-config", "session_fork": "--fork-session",
            "tmux": "--tmux", "tool_allowlist": "--allowed-tools",
        },
    },
    "grok": {
        "version_command": ["grok", "--version"],
        "help_commands": [["grok", "--help"]],
        "tokens": {
            "non_interactive": "--single", "structured_output": "--json-schema",
            "streaming_json": "streaming-json", "permission_modes": "--permission-mode",
            "subagents": "--agents", "best_of_n": "--best-of-n", "self_check": "--check",
            "session_fork": "--fork-session", "resume": "--resume", "memory": "--experimental-memory",
            "plan_mode": "--no-plan", "worktrees": "--worktree", "sandbox": "--sandbox",
            "web_search": "web search", "effort_control": "--reasoning-effort",
            "max_turns": "--max-turns", "oauth": "--oauth", "inspect_receipt": "inspect",
            "mcp": "mcp", "plugins": "plugin", "plugin_marketplace": "marketplace",
            "dashboard": "dashboard", "sessions": "sessions", "tool_allowlist": "--allow",
            "approval_bypass": "--always-approve", "claude_compat": "claude code",
        },
    },
    "hermes": {
        "version_command": ["hermes", "--version"],
        "help_commands": [["hermes", "--help"]],
        "tokens": {
            "non_interactive": "--oneshot", "profiles": "profiles", "skills": "skills",
            "mcp": "mcp", "plugins": "plugins", "memory": "memory", "cron": "cron",
            "gateway": "gateway", "security": "security", "worktrees": "--worktree",
            "safe_mode": "--safe-mode", "approval_bypass": "--yolo", "fallback_chain": "fallback",
            "credential_pools": "pooled credential", "kanban": "kanban", "hooks": "hooks",
            "backups": "backup", "checkpoints": "checkpoints", "bundles": "bundles",
            "curator": "curator", "toolsets": "--toolsets", "computer_use": "computer-use",
            "sessions": "sessions", "acp": "acp", "dashboard": "dashboard",
            "ignore_user_config": "--ignore-user-config", "ignore_rules": "--ignore-rules",
        },
    },
    "portage": {
        "version_command": ["portage", "--version"],
        "help_commands": [["portage", "--help"]],
        "tokens": {
            "snapshot": "snapshot", "pack": "pack", "delta": "delta", "doctor": "doctor",
            "provider_discovery": "providers", "open_hint": "open",
        },
    },
}

CONTEXT_NAMES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", ".hermes.md")
SIGNALS = {
    "codex_thread": "CODEX_THREAD_ID",
    "claude_session": "CLAUDE_CODE_SESSION_ID",
    "claude_entrypoint": "CLAUDE_CODE_ENTRYPOINT",
    "hermes_home": "HERMES_HOME",
    "portage_present": "PORTAGE_HOME",
}


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run(command: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, env={**os.environ, "NO_COLOR": "1"})
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode, output


def git_root(cwd: Path) -> Path:
    result = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else cwd


def context_inventory(cwd: Path, root: Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    current = cwd
    ancestor_depth = 0
    while True:
        for name in CONTEXT_NAMES:
            path = current / name
            if path.is_file() and not path.is_symlink():
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    relative = f"@ancestor/{ancestor_depth}/{name}"
                found.append({"kind": name, "path": relative, "sha256": sha(path.read_bytes())})
        if current.parent == current or ancestor_depth >= 8:
            break
        current = current.parent
        if current != root and root not in current.parents:
            ancestor_depth += 1
    return sorted(found, key=lambda item: (item["path"].count("/"), item["path"], item["kind"]))


def capture(cwd: Path) -> dict[str, object]:
    root = git_root(cwd)
    hosts = []
    for host_id, spec in HOSTS.items():
        binary = shutil.which(host_id)
        if not binary:
            hosts.append({"id": host_id, "installed": False, "executable_name": host_id, "executable_sha256": None,
                          "version": None, "version_output_sha256": None, "help_output_sha256": None,
                          "capabilities": [], "probe_errors": []})
            continue
        version_rc, version = run(spec["version_command"])
        help_results = [run(command) for command in spec["help_commands"]]
        help_rc = 0 if all(code == 0 for code, _ in help_results) else 1
        help_text = "\n\n".join(output for _, output in help_results)
        normalized = help_text.lower()
        capabilities = sorted(name for name, token in spec["tokens"].items() if token.lower() in normalized)
        errors = []
        if version_rc != 0:
            errors.append("version_probe_failed")
        if help_rc != 0:
            errors.append("help_probe_failed")
        binary_path = Path(binary).resolve()
        try:
            binary_hash = sha(binary_path.read_bytes())
        except OSError:
            binary_hash = None
            errors.append("executable_hash_failed")
        hosts.append({"id": host_id, "installed": True, "executable_name": host_id,
                      "executable_sha256": binary_hash, "version": version.splitlines()[0][:240] if version else None,
                      "version_output_sha256": sha(version.encode()) if version else None,
                      "help_output_sha256": sha(help_text.encode()) if help_text else None,
                      "capabilities": capabilities, "probe_errors": errors})
    relative_cwd = "."
    try:
        relative_cwd = cwd.relative_to(root).as_posix() or "."
    except ValueError:
        pass
    return {
        "schema_version": 1,
        "receipt_kind": "captured_inventory",
        "captured_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace": {"cwd": relative_cwd, "git_root_name": root.name, "git_head": _git_head(root)},
        "runtime_signals": {name: bool(os.environ.get(variable)) for name, variable in SIGNALS.items()},
        "context_files": context_inventory(cwd, root),
        "hosts": hosts,
        "limitations": [
            "Help text proves advertised local CLI surface, not feature enablement or authorization.",
            "Environment signal presence is recorded without values and does not prove active-host identity.",
            "Effective sandbox, approval, network, credentials, model, and managed policy require host-native evidence.",
        ],
        "decision": {"outcome": "inventory_only", "reasons": ["Capability negotiation requires task-specific authority review."]},
    }


def _git_head(root: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    value = result.stdout.strip().lower()
    return value if result.returncode == 0 and len(value) == 40 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--output")
    args = parser.parse_args()
    cwd = Path(args.cwd).resolve()
    if not cwd.is_dir():
        parser.error("--cwd must be an existing directory")
    payload = json.dumps(capture(cwd), indent=2) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            create_new_text(output, payload)
        except OSError as exc:
            print(f"cannot publish host capability receipt: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
