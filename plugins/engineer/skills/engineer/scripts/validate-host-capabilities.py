#!/usr/bin/env python3
"""Validate a secret-safe coding-agent host capability inventory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HOST_IDS = {"codex", "claude", "grok", "hermes", "portage"}
CAPABILITIES = {
    "codex": {"non_interactive", "mcp", "mcp_server", "sandbox", "approvals", "resume", "profiles", "web_search", "cloud", "feature_flags", "structured_output", "strict_config", "code_review", "plugins", "app_server", "remote_control", "remote_client", "session_fork", "session_archive", "local_provider", "hooks", "plugin_marketplace", "feature_toggles", "exec_server", "profile_as_file"},
    "claude": {"non_interactive", "mcp", "plugins", "permission_modes", "resume", "worktrees", "subagents", "background_agents", "structured_output", "streaming_json", "browser", "bare_mode", "no_persistence", "safe_mode", "remote_control", "cloud_review", "fallback_model", "effort_control", "cost_budget", "strict_mcp", "session_fork", "tmux", "tool_allowlist"},
    "grok": {"non_interactive", "structured_output", "streaming_json", "permission_modes", "subagents", "best_of_n", "self_check", "session_fork", "resume", "memory", "plan_mode", "worktrees", "sandbox", "web_search", "effort_control", "max_turns", "oauth", "inspect_receipt", "mcp", "plugins", "plugin_marketplace", "dashboard", "sessions", "tool_allowlist", "approval_bypass", "claude_compat"},
    "hermes": {"non_interactive", "profiles", "skills", "mcp", "plugins", "memory", "cron", "gateway", "security", "worktrees", "safe_mode", "approval_bypass", "fallback_chain", "credential_pools", "kanban", "hooks", "backups", "checkpoints", "bundles", "curator", "toolsets", "computer_use", "sessions", "acp", "dashboard", "ignore_user_config", "ignore_rules"},
    "portage": {"snapshot", "pack", "delta", "doctor", "provider_discovery", "open_hint"},
}
LIMITATIONS = {
    "Help text proves advertised local CLI surface, not feature enablement or authorization.",
    "Environment signal presence is recorded without values and does not prove active-host identity.",
    "Effective sandbox, approval, network, credentials, model, and managed policy require host-native evidence.",
}


def safe_relative(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts


def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    root_keys = {"schema_version", "receipt_kind", "captured_at", "workspace", "runtime_signals", "context_files", "hosts", "limitations", "decision"}
    if not isinstance(data, dict):
        return ["root must be an object"], []
    if set(data) != root_keys:
        errors.append("root keys invalid")
    if data.get("schema_version") != 1 or data.get("receipt_kind") not in {"illustrative_fixture", "captured_inventory"}:
        errors.append("schema or receipt kind invalid")
    if not isinstance(data.get("captured_at"), str) or "T" not in data.get("captured_at", ""):
        errors.append("captured_at invalid")
    workspace = data.get("workspace", {})
    if not isinstance(workspace, dict) or set(workspace) != {"cwd", "git_root_name", "git_head"} or not safe_relative(workspace.get("cwd")) or not isinstance(workspace.get("git_root_name"), str) or not workspace.get("git_root_name") or (workspace.get("git_head") is not None and not HEX40.fullmatch(workspace.get("git_head", ""))):
        errors.append("workspace invalid")
    signals = data.get("runtime_signals", {})
    if not isinstance(signals, dict) or set(signals) != {"codex_thread", "claude_session", "claude_entrypoint", "hermes_home", "portage_present"} or any(type(value) is not bool for value in signals.values()):
        errors.append("runtime signals invalid")
    contexts = data.get("context_files")
    seen_paths: set[str] = set()
    if not isinstance(contexts, list):
        errors.append("context_files must be an array")
        contexts = []
    for item in contexts:
        if not isinstance(item, dict) or set(item) != {"kind", "path", "sha256"} or item.get("kind") not in {"AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", ".hermes.md"} or not safe_relative(item.get("path")) or not HEX64.fullmatch(item.get("sha256", "")):
            errors.append("context file invalid")
            continue
        if item["path"] in seen_paths:
            gates.append("context paths must be unique")
        seen_paths.add(item["path"])
    hosts = data.get("hosts")
    seen_hosts: set[str] = set()
    host_keys = {"id", "installed", "executable_name", "executable_sha256", "version", "version_output_sha256", "help_output_sha256", "capabilities", "probe_errors"}
    if not isinstance(hosts, list) or len(hosts) != 5:
        errors.append("hosts must contain exactly five known hosts")
        hosts = []
    for host in hosts:
        if not isinstance(host, dict) or set(host) != host_keys or host.get("id") not in HOST_IDS or host.get("id") in seen_hosts:
            errors.append("host identity or keys invalid")
            continue
        host_id = host["id"]
        seen_hosts.add(host_id)
        if type(host.get("installed")) is not bool or host.get("executable_name") != host_id:
            errors.append(f"{host_id} install or executable identity invalid")
        caps = host.get("capabilities")
        if not isinstance(caps, list) or caps != sorted(set(caps)) or not set(caps) <= CAPABILITIES[host_id]:
            errors.append(f"{host_id} capabilities invalid")
        probe_errors = host.get("probe_errors")
        if not isinstance(probe_errors, list) or not set(probe_errors) <= {"version_probe_failed", "help_probe_failed", "executable_hash_failed"} or len(probe_errors) != len(set(probe_errors)):
            errors.append(f"{host_id} probe errors invalid")
        hashes = (host.get("executable_sha256"), host.get("version_output_sha256"), host.get("help_output_sha256"))
        if host.get("installed"):
            if host.get("version") is not None and (not isinstance(host.get("version"), str) or len(host["version"]) > 240):
                errors.append(f"{host_id} version invalid")
            for value in hashes:
                if value is not None and not HEX64.fullmatch(value):
                    errors.append(f"{host_id} hash invalid")
            if not host.get("probe_errors") and (not host.get("version") or any(value is None for value in hashes)):
                gates.append(f"{host_id} successful probes require version and hashes")
        elif any(value is not None for value in (*hashes, host.get("version"))) or caps or probe_errors:
            gates.append(f"{host_id} absent host carries observed data")
    if seen_hosts != HOST_IDS:
        errors.append("known host set incomplete")
    limitations = data.get("limitations")
    if not isinstance(limitations, list) or set(limitations) != LIMITATIONS or len(limitations) != 3:
        gates.append("mandatory evidence limitations missing or altered")
    decision = data.get("decision", {})
    if not isinstance(decision, dict) or set(decision) != {"outcome", "reasons"} or decision.get("outcome") != "inventory_only" or not isinstance(decision.get("reasons"), list) or not decision.get("reasons") or not all(isinstance(reason, str) and reason for reason in decision["reasons"]):
        errors.append("inventory-only decision invalid")
    return errors, gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        receipt = regular_input_file(args.receipt)
        if receipt is None:
            raise ValueError("receipt must be a regular file, not a symlink")
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors, gates = [str(exc)], []
    else:
        errors, gates = validate(data)
    if args.json:
        print(json.dumps({"ok": not errors and not gates, "errors": errors, "gates": gates}, indent=2))
    else:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        for message in gates:
            print(f"GATE: {message}", file=sys.stderr)
        if not errors and not gates:
            print("host capability inventory valid")
    return 0 if not errors and not gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
