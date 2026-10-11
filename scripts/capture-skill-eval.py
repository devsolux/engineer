#!/usr/bin/env python3
"""Compile and optionally execute sealed cross-host skill-evaluation jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import is_under, regular_input_file, relative_posix, safe_path

FORBIDDEN_KEYS = {
    "assertions",
    "expected",
    "expected_output",
    "golden",
    "grader",
    "graders",
    "promotion",
    "reference_answer",
    "rubric",
}
ROOT_KEYS = {
    "schema_version",
    "run_kind",
    "run_id",
    "host",
    "host_inventory",
    "authentication",
    "skill_bundle",
    "model",
    "scenario",
    "workspace",
    "fixture_marker",
    "permissions",
    "budgets",
    "output_dir",
}

BUNDLE_INCLUDE = ("SKILL.md", "COMPAT.md", "agents", "commands", "references", "scripts", "templates")
BUNDLE_EXCLUDE_PREFIXES = (
    "scripts/capture-skill-eval.py",
    "scripts/test-skill-eval-capture",
    "scripts/validate-skill-eval-capture.py",
    "templates/agentic/host-capabilities",
    "templates/agentic/skill-eval",
    "templates/agentic/engineer-telemetry",
    "templates/fixtures/skill-eval",
)
PLUGIN_DIR_PLACEHOLDER = "<ISOLATED_ENGINEER_PLUGIN>"
VERSION_RE = re.compile(r'^  version: "([^"]+)"$', re.MULTILINE)
REFERENCE_RE = re.compile(r"references/([a-z0-9-]+\.md)")
ACTIVATION_FAILURE = re.compile(
    r"(?i)(unknown skill|skill (?:was )?not found|could not (?:find|load) (?:the )?skill|unknown slash command|not a valid (?:skill|slash command))"
)
ACTIVATION_PROBE_REQUEST = "[routing-probe:alpha]"
ACTIVATION_PROBE_RESPONSE = "ENGINEER_ROUTING_ACTIVE_v1"
ACTIVATION_PROBE_SHA256 = hashlib.sha256(ACTIVATION_PROBE_RESPONSE.encode()).hexdigest()
HOST_REQUIRED_CAPABILITIES = {
    "codex": ["approvals", "non_interactive", "sandbox", "strict_config"],
    "claude": ["bare_mode", "no_persistence", "non_interactive", "permission_modes", "streaming_json"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_files(source_root: Path) -> list[Path]:
    """Return the deterministic, expectation-free runtime package file set."""
    files: list[Path] = []
    for entry in BUNDLE_INCLUDE:
        path = source_root / entry
        if not path.exists():
            raise ValueError(f"skill bundle required entry missing: {entry}")
        if path.is_symlink():
            raise ValueError(f"skill bundle rejects symlink: {entry}")
        candidates = [path] if path.is_file() else sorted(path.rglob("*")) if path.is_dir() else []
        for candidate in candidates:
            relative = relative_posix(candidate, source_root)
            if "__pycache__" in relative.split("/") or candidate.suffix in {".pyc", ".pyo"}:
                continue
            if any(relative == prefix or relative.startswith(prefix) for prefix in BUNDLE_EXCLUDE_PREFIXES):
                continue
            if candidate.is_symlink():
                raise ValueError(f"skill bundle rejects symlink: {relative}")
            if candidate.is_file():
                files.append(candidate)
    return sorted(files, key=lambda path: relative_posix(path, source_root))


def validate_bundle_structure(source_root: Path, declared_version: str) -> list[str]:
    errors: list[str] = []
    try:
        files = bundle_files(source_root)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    skill = source_root / "SKILL.md"
    match = VERSION_RE.search(skill.read_text(encoding="utf-8"))
    if match is None or match.group(1) != declared_version:
        errors.append("skill_bundle.version must match SKILL.md metadata.version")
    packaged = {relative_posix(path, source_root) for path in files}
    for path in files:
        relative_path = relative_posix(path, source_root)
        if path.suffix != ".md" or (relative_path != "SKILL.md" and not relative_path.startswith("commands/")):
            continue
        for reference in REFERENCE_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
            target = f"references/{reference}"
            if target not in packaged:
                errors.append(f"packaged reference unresolved: {relative_path} -> {target}")
    return sorted(set(errors))


def bundle_sha256(source_root: Path) -> str:
    digest = hashlib.sha256()
    for path in bundle_files(source_root):
        relative = relative_posix(path, source_root).encode()
        executable = b"1" if path.stat().st_mode & 0o111 else b"0"
        body = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(executable)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    return digest.hexdigest()


def copy_skill_bundle(source_root: Path, target: Path, expected_sha256: str) -> None:
    if target.exists() and any(target.iterdir()):
        raise ValueError("runtime skill bundle target must be empty")
    target.mkdir(parents=True, mode=0o700)
    for source in bundle_files(source_root):
        relative = Path(relative_posix(source, source_root))
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination, follow_symlinks=False)
    if bundle_sha256(target) != expected_sha256:
        raise ValueError("copied skill bundle digest differs from bound source package")
    for forbidden in ("evals", "research", ".git", ".engineer"):
        if (target / forbidden).exists():
            raise ValueError(f"forbidden skill-bundle content copied: {forbidden}")


def prepare_runtime_bundle(data: dict[str, Any], root: Path, isolated_home: Path) -> Path | None:
    source_root = (root / data["skill_bundle"]["source_root"]).resolve()
    if data["host"] == "codex":
        copy_skill_bundle(source_root, isolated_home / ".codex" / "skills" / "engineer", data["skill_bundle"]["sha256"])
        return None
    plugin = isolated_home / "engineer-eval-plugin"
    copy_skill_bundle(source_root, plugin / "skills" / "engineer", data["skill_bundle"]["sha256"])
    manifest = plugin / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    write_json(manifest, {"name": "engineer-eval", "description": "Sealed engineer behavioral evaluation package", "version": data["skill_bundle"]["version"], "author": {"name": "devsolux"}})
    return plugin


def find_forbidden_keys(value: Any, path: str = "root") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(find_forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(find_forbidden_keys(child, f"{path}[{index}]"))
    return hits


def load_host_inventory(data: dict[str, Any], root: Path, errors: list[str]) -> dict[str, Any] | None:
    binding = data.get("host_inventory")
    keys = {"path", "sha256", "host", "executable_sha256", "version_output_sha256", "help_output_sha256", "required_capabilities"}
    if not isinstance(binding, dict) or set(binding) != keys:
        errors.append(f"host_inventory keys must be exactly {sorted(keys)}")
        return None
    if binding.get("host") != data.get("host"):
        errors.append("host_inventory.host must match job host")
    path = safe_path(binding.get("path"), root)
    if path is None or not path.is_file():
        errors.append("host_inventory.path must be an existing repository-relative file")
        return None
    if not isinstance(binding.get("sha256"), str) or sha256(path) != binding.get("sha256"):
        errors.append("host_inventory.sha256 does not match inventory file")
        return None
    validator = Path(__file__).with_name("validate-host-capabilities.py")
    result = subprocess.run([sys.executable, str(validator), str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("host inventory fails canonical validation")
        return None
    try:
        inventory = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append("host inventory cannot be parsed")
        return None
    matches = [item for item in inventory.get("hosts", []) if isinstance(item, dict) and item.get("id") == data.get("host")]
    if len(matches) != 1 or matches[0].get("installed") is not True:
        errors.append("selected host must be installed in bound inventory")
        return None
    observed = matches[0]
    for key in ("executable_sha256", "version_output_sha256", "help_output_sha256"):
        value = binding.get(key)
        if not isinstance(value, str) or value != observed.get(key):
            errors.append(f"host_inventory.{key} must match selected host evidence")
    required = binding.get("required_capabilities")
    expected = HOST_REQUIRED_CAPABILITIES.get(data.get("host"))
    if not isinstance(required, list) or required != expected or not set(required) <= set(observed.get("capabilities", [])):
        errors.append("host_inventory.required_capabilities must exactly match the sorted adapter policy and be observed")
    return inventory


def validate_job(data: Any, root: Path, executing: bool) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["job root must be an object"]
    if set(data) != ROOT_KEYS:
        errors.append(f"root keys must be exactly {sorted(ROOT_KEYS)}")
    if data.get("schema_version") != 5:
        errors.append("schema_version must be 5")
    run_kind = data.get("run_kind")
    if run_kind not in {"illustrative_fixture", "captured_run"}:
        errors.append("run_kind must be illustrative_fixture or captured_run")
    if executing and run_kind != "captured_run":
        errors.append("only captured_run jobs may execute")
    for key in ("run_id", "model"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"{key} must be a non-empty string")
    run_id = data.get("run_id")
    if isinstance(run_id, str) and (not run_id.replace("-", "").replace("_", "").isalnum() or len(run_id) > 96):
        errors.append("run_id must be <=96 safe identifier characters")
    host = data.get("host")
    if host not in {"codex", "claude"}:
        errors.append("host must be codex or claude")
    inventory = load_host_inventory(data, root, errors)
    if executing and isinstance(inventory, dict) and inventory.get("receipt_kind") != "captured_inventory":
        errors.append("execution requires a captured host inventory")

    authentication = data.get("authentication")
    auth_keys = {"mode", "api_key_env", "isolated_home", "cached_credentials_allowed", "keyring_allowed"}
    expected_api_key = "CODEX_API_KEY" if host == "codex" else "ANTHROPIC_API_KEY"
    if not isinstance(authentication, dict) or set(authentication) != auth_keys:
        errors.append(f"authentication keys must be exactly {sorted(auth_keys)}")
    elif authentication.get("mode") != "api_key_env" or authentication.get("api_key_env") != expected_api_key or authentication.get("isolated_home") is not True or authentication.get("cached_credentials_allowed") is not False or authentication.get("keyring_allowed") is not False:
        errors.append(f"{host} capture requires isolated {expected_api_key} authentication without cached credentials or keyring")
    bundle = data.get("skill_bundle")
    bundle_keys = {"source_root", "sha256", "version", "include", "exclude_prefixes", "expectations_excluded"}
    if not isinstance(bundle, dict) or set(bundle) != bundle_keys:
        errors.append(f"skill_bundle keys must be exactly {sorted(bundle_keys)}")
    else:
        source_root = safe_path(bundle.get("source_root"), root)
        if source_root is None or not source_root.is_dir():
            errors.append("skill_bundle.source_root must be an existing repository-relative directory")
        if bundle.get("include") != list(BUNDLE_INCLUDE) or bundle.get("exclude_prefixes") != list(BUNDLE_EXCLUDE_PREFIXES):
            errors.append("skill_bundle include/exclude policy must match the canonical expectation-free package")
        if bundle.get("expectations_excluded") is not True:
            errors.append("skill_bundle.expectations_excluded must be true")
        if not isinstance(bundle.get("version"), str) or not bundle["version"].strip():
            errors.append("skill_bundle.version must be a non-empty string")
        if source_root is not None and source_root.is_dir():
            errors.extend(validate_bundle_structure(source_root, str(bundle.get("version", ""))))
            try:
                observed_bundle_sha256 = bundle_sha256(source_root)
            except (OSError, ValueError) as exc:
                errors.append(str(exc))
            else:
                if bundle.get("sha256") != observed_bundle_sha256:
                    errors.append("skill_bundle.sha256 does not match the canonical runtime package")
    leaks = find_forbidden_keys(data)
    if leaks:
        errors.append(f"job contains forbidden expectation/grader keys: {leaks}")

    scenario = data.get("scenario")
    scenario_keys = {"id", "activation_mode", "invocation", "activation_probe", "source_path", "source_sha256", "expectations_exposed"}
    if not isinstance(scenario, dict) or set(scenario) != scenario_keys:
        errors.append(f"scenario keys must be exactly {sorted(scenario_keys)}")
        scenario = {}
    if not isinstance(scenario.get("id"), int) or isinstance(scenario.get("id"), bool) or scenario.get("id", 0) < 1:
        errors.append("scenario.id must be a positive integer")
    if scenario.get("expectations_exposed") is not False:
        errors.append("scenario.expectations_exposed must be false")
    activation_mode = scenario.get("activation_mode")
    if activation_mode not in {"explicit", "implicit"}:
        errors.append("scenario.activation_mode must be explicit or implicit")
    expected_invocation = "$engineer" if host == "codex" else "/engineer-eval:engineer"
    if activation_mode == "explicit" and scenario.get("invocation") != expected_invocation:
        errors.append(f"explicit scenario.invocation must be {expected_invocation} for {host}")
    if activation_mode == "implicit" and scenario.get("invocation") is not None:
        errors.append("implicit scenario.invocation must be null")
    probe = scenario.get("activation_probe")
    if not isinstance(probe, dict) or set(probe) != {"request", "response_sha256"} or probe.get("request") != ACTIVATION_PROBE_REQUEST or probe.get("response_sha256") != ACTIVATION_PROBE_SHA256:
        errors.append("scenario.activation_probe must match the canonical sealed routing probe")
    source_path = safe_path(scenario.get("source_path"), root)
    if source_path is None or not source_path.is_file():
        errors.append("scenario.source_path must be an existing repository-relative file")
    elif not isinstance(scenario.get("source_sha256"), str) or sha256(source_path) != scenario.get("source_sha256"):
        errors.append("scenario.source_sha256 does not match the source file")
    else:
        try:
            source = json.loads(source_path.read_text(encoding="utf-8"))
            items = source.get("evals", []) if isinstance(source, dict) else []
            matches = [item for item in items if isinstance(item, dict) and item.get("id") == scenario.get("id")]
        except (OSError, json.JSONDecodeError):
            matches = []
        if len(matches) != 1 or not isinstance(matches[0].get("prompt"), str) or len(matches[0]["prompt"].strip()) < 10:
            errors.append("scenario id must resolve to exactly one meaningful prompt in the source")
        elif activation_mode == "implicit" and re.search(r"(?i)(?:\$|/)?engineer", matches[0]["prompt"]):
            errors.append("implicit scenario prompt must not contain the engineer name or invocation")

    workspace = safe_path(data.get("workspace"), root)
    if workspace is None or not workspace.is_dir():
        errors.append("workspace must be an existing repository-relative directory")
    marker = data.get("fixture_marker")
    if not isinstance(marker, str) or not marker or "/" in marker or marker in {".", ".."}:
        errors.append("fixture_marker must be a safe filename")
    elif workspace is not None and not (workspace / marker).is_file():
        errors.append("workspace is missing its fixture marker")

    output_dir = safe_path(data.get("output_dir"), root)
    captures_root = (root / ".engineer" / "eval-captures").resolve()
    if output_dir is None:
        errors.append("output_dir must be repository-relative")
    else:
        if not is_under(output_dir, captures_root):
            errors.append("output_dir must stay under .engineer/eval-captures")
    if workspace is not None and output_dir is not None and (output_dir == workspace or workspace in output_dir.parents):
        errors.append("capture output must be outside the tested workspace")

    permissions = data.get("permissions")
    permission_keys = {"sandbox", "network", "allowed_tools", "external_writes"}
    if not isinstance(permissions, dict) or set(permissions) != permission_keys:
        errors.append(f"permissions keys must be exactly {sorted(permission_keys)}")
        permissions = {}
    if permissions.get("sandbox") not in {"read_only", "workspace_write"}:
        errors.append("permissions.sandbox must be read_only or workspace_write")
    if permissions.get("network") != "deny":
        errors.append("behavioral capture currently requires denied tool network")
    if permissions.get("external_writes") is not False:
        errors.append("permissions.external_writes must be false")
    tools = permissions.get("allowed_tools")
    if not isinstance(tools, list) or not tools or any(not isinstance(tool, str) or not tool for tool in tools):
        errors.append("permissions.allowed_tools must contain named tools")
    elif len(set(tools)) != len(tools):
        errors.append("permissions.allowed_tools must be unique")
    if host == "claude" and isinstance(tools, list) and set(tools) != {"Read", "Glob", "Grep"}:
        errors.append("Claude capture requires exactly the logical Read, Glob, and Grep tool set")
    if host == "codex" and permissions.get("sandbox") != "read_only":
        errors.append("Codex capture currently requires read_only sandbox")

    budgets = data.get("budgets")
    budget_keys = {"timeout_seconds", "max_turns", "max_cost_usd"}
    if not isinstance(budgets, dict) or set(budgets) != budget_keys:
        errors.append(f"budgets keys must be exactly {sorted(budget_keys)}")
        budgets = {}
    for key, lower, upper in (("timeout_seconds", 30, 1800), ("max_turns", 1, 64)):
        value = budgets.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not lower <= value <= upper:
            errors.append(f"budgets.{key} must be an integer in {lower}..{upper}")
    cost = budgets.get("max_cost_usd")
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or not 0 < cost <= 100:
        errors.append("budgets.max_cost_usd must be within 0..100")
    return errors


def verify_live_host(data: dict[str, Any], root: Path) -> tuple[bool, str]:
    capture = Path(__file__).with_name("capture-host-capabilities.py")
    with tempfile.TemporaryDirectory(prefix="engineer-host-probe-") as directory:
        path = Path(directory) / "inventory.json"
        result = subprocess.run(
            [sys.executable, str(capture), "--cwd", str(root), "--output", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 or not path.is_file():
            return False, "live host capability capture failed"
        try:
            inventory = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False, "live host capability capture is unreadable"
    matches = [item for item in inventory.get("hosts", []) if item.get("id") == data["host"]]
    if len(matches) != 1 or matches[0].get("installed") is not True:
        return False, "selected host is not installed in live inventory"
    observed = matches[0]
    binding = data["host_inventory"]
    for key in ("executable_sha256", "version_output_sha256", "help_output_sha256"):
        if observed.get(key) != binding.get(key):
            return False, f"live host {key} drifted from reviewed inventory"
    if not set(binding["required_capabilities"]) <= set(observed.get("capabilities", [])):
        return False, "live host no longer advertises every required capability"
    return True, "live host identity and advertised surface match reviewed inventory"


def prompt_for(data: dict[str, Any], root: Path) -> str:
    scenario = data["scenario"]
    source = json.loads((root / scenario["source_path"]).read_text(encoding="utf-8"))
    prompt = next(item["prompt"] for item in source["evals"] if item["id"] == scenario["id"])
    parts = []
    if scenario["activation_mode"] == "explicit":
        parts.append(scenario["invocation"])
    parts.extend([prompt, scenario["activation_probe"]["request"]])
    return "\n\n".join(parts)


def activation_probe_confirmed(body: str) -> bool:
    return sum(line.strip() == ACTIVATION_PROBE_RESPONSE for line in body.splitlines()) == 1


def activation_failure_reason(*bodies: str) -> str | None:
    for body in bodies:
        match = ACTIVATION_FAILURE.search(body)
        if match:
            return match.group(1).lower()
    return None


def command_for(data: dict[str, Any], root: Path, final_path: Path) -> list[str]:
    host = data["host"]
    model = data["model"]
    prompt = prompt_for(data, root)
    workspace = str((root / data["workspace"]).resolve())
    if host == "codex":
        command = [
            "codex",
            "-a",
            "never",
            "-c",
            "shell_environment_policy.inherit=none",
            "-c",
            'web_search="disabled"',
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--strict-config",
            "--ignore-rules",
            "--sandbox",
            "read-only",
            "--json",
            "--color",
            "never",
            "-C",
            workspace,
            "-o",
            str(final_path),
        ]
        if model != "default":
            command.extend(["--model", model])
        command.append(prompt)
        return command
    command = [
        "claude",
        "--bare",
        "--plugin-dir",
        PLUGIN_DIR_PLACEHOLDER,
        "--print",
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--permission-mode",
        "dontAsk",
        "--max-turns",
        str(data["budgets"]["max_turns"]),
        "--max-budget-usd",
        str(data["budgets"]["max_cost_usd"]),
        "--allowedTools",
        "Read(./**)",
        "--disallowedTools",
        "Bash",
        "Edit",
        "Write",
        "WebFetch",
        "WebSearch",
        "Agent",
        "NotebookEdit",
    ]
    if model != "default":
        command.extend(["--model", model])
    command.append(prompt)
    return command


def logical_command_sha256(command: list[str], root: Path) -> str:
    """Hash policy-relevant argv without binding the receipt to one checkout path."""
    root_text = str(root.resolve())
    canonical = [part.replace(root_text, "<REPOSITORY_ROOT>") for part in command]
    return hashlib.sha256(json.dumps(canonical).encode()).hexdigest()


def sanitized_environment(host: str, isolated_home: Path) -> dict[str, str]:
    keep = {"PATH", "SHELL", "TMPDIR", "LANG", "LC_ALL"}
    if host == "codex":
        keep.add("CODEX_API_KEY")
    else:
        keep.add("ANTHROPIC_API_KEY")
    env = {key: value for key, value in os.environ.items() if key in keep}
    env["HOME"] = str(isolated_home)
    if host == "codex":
        env["CODEX_HOME"] = str(isolated_home / ".codex")
        Path(env["CODEX_HOME"]).mkdir(mode=0o700)
    else:
        env["CLAUDE_CONFIG_DIR"] = str(isolated_home / ".claude")
        Path(env["CLAUDE_CONFIG_DIR"]).mkdir(mode=0o700)
    env["CI"] = "1"
    env["NO_COLOR"] = "1"
    env["DISABLE_AUTOUPDATER"] = "1"
    return env


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def execute(data: dict[str, Any], root: Path, job_path: Path) -> int:
    host_ok, host_reason = verify_live_host(data, root)
    if not host_ok:
        print(host_reason, file=sys.stderr)
        return 2
    try:
        relative_job = relative_posix(job_path, root)
    except ValueError:
        print("executed job file must stay inside the repository", file=sys.stderr)
        return 2
    output_dir = (root / data["output_dir"]).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        print("capture output directory already exists and is not empty", file=sys.stderr)
        return 2
    final_path = output_dir / "final.md"
    stdout_path = output_dir / "trace.jsonl"
    stderr_path = output_dir / "runner.stderr.log"
    logical_command = command_for(data, root, final_path)
    logical_command_digest = logical_command_sha256(logical_command, root)
    executable = shutil.which(logical_command[0])
    if executable is None:
        print(f"host executable not found: {logical_command[0]}", file=sys.stderr)
        return 2
    key_name = data["authentication"]["api_key_env"]
    if not os.environ.get(key_name):
        print(f"captured execution requires {key_name} in the runner environment", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="engineer-eval-home-") as home_dir:
        isolated_home = Path(home_dir)
        try:
            plugin = prepare_runtime_bundle(data, root, isolated_home)
            command = [str(plugin) if item == PLUGIN_DIR_PLACEHOLDER else item for item in logical_command]
            command[0] = executable
            completed = subprocess.run(
                command,
                cwd=(root / data["workspace"]).resolve(),
                env=sanitized_environment(data["host"], isolated_home),
                text=True,
                capture_output=True,
                timeout=data["budgets"]["timeout_seconds"],
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            timed_out = False
        except (OSError, ValueError) as exc:
            print(f"runtime skill bundle preparation failed: {exc}", file=sys.stderr)
            return 2
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            timed_out = True
    duration_ms = round((time.monotonic() - start) * 1000)
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    if data["host"] == "claude" and not final_path.exists():
        final = ""
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "result" and isinstance(event.get("result"), str):
                final = event["result"]
        final_path.write_text(final, encoding="utf-8")
    if not final_path.exists():
        final_path.write_text("", encoding="utf-8")
    final_body = final_path.read_text(encoding="utf-8", errors="replace")
    activation_failure = activation_failure_reason(stdout, stderr, final_body)
    activation_confirmed = activation_probe_confirmed(final_body)
    manifest = {
        "schema_version": 5,
        "capture_kind": "captured_run",
        "run_id": data["run_id"],
        "job": {"path": relative_job, "sha256": sha256(job_path.resolve())},
        "host": data["host"],
        "model": data["model"],
        "scenario_id": data["scenario"]["id"],
        "host_binding": {
            "inventory_sha256": data["host_inventory"]["sha256"],
            "executable_sha256": data["host_inventory"]["executable_sha256"],
            "version_output_sha256": data["host_inventory"]["version_output_sha256"],
            "help_output_sha256": data["host_inventory"]["help_output_sha256"],
            "required_capabilities": data["host_inventory"]["required_capabilities"],
            "live_reverified": True,
            "reason": host_reason,
        },
        "skill_binding": {
            "sha256": data["skill_bundle"]["sha256"],
            "version": data["skill_bundle"]["version"],
            "expectations_excluded": True,
            "runtime_supplied": True,
            "activation_mode": data["scenario"]["activation_mode"],
            "invocation": data["scenario"]["invocation"],
            "activation_probe_sha256": data["scenario"]["activation_probe"]["response_sha256"],
            "activation_confirmed": activation_confirmed,
            "mechanism": "codex_home_skill" if data["host"] == "codex" else "claude_plugin",
            "unresolved_marker_absent": activation_failure is None,
        },
        "execution": {
            "exit_code": exit_code,
            "timed_out": timed_out,
            "duration_ms": duration_ms,
            "logical_command_sha256": logical_command_digest,
            "executed_argv_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
        },
        "artifacts": [
            {"kind": "output", "path": relative_posix(final_path, root), "sha256": sha256(final_path), "bytes": final_path.stat().st_size},
            {"kind": "trace", "path": relative_posix(stdout_path, root), "sha256": sha256(stdout_path), "bytes": stdout_path.stat().st_size},
            {"kind": "log", "path": relative_posix(stderr_path, root), "sha256": sha256(stderr_path), "bytes": stderr_path.stat().st_size},
        ],
        "assessment": {
            "capture_succeeded": exit_code == 0 and not timed_out and activation_failure is None and activation_confirmed,
            "behavioral_pass": None,
            "grading_required": True,
        },
        "limitations": [
            "Capture success is not behavioral success or promotion evidence.",
            "Local hashes do not prove runner, sandbox, network, credential, or provider honesty.",
            "Artifacts require independent outcome and trajectory grading after secret review.",
        ],
    }
    manifest_path = output_dir / "capture.json"
    write_json(manifest_path, manifest)
    validator = Path(__file__).with_name("validate-skill-eval-capture.py")
    validation = subprocess.run(
        [sys.executable, str(validator), str(manifest_path), "--root", str(root)],
        capture_output=True,
        text=True,
    )
    if validation.returncode != 0:
        print("capture artifacts failed canonical integrity or secret review", file=sys.stderr)
        print(validation.stderr.strip(), file=sys.stderr)
        print(json.dumps(manifest, indent=2))
        return 2
    print(json.dumps(manifest, indent=2))
    return 0 if exit_code == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--print-command", action="store_true", help="validate and print argv without executing")
    parser.add_argument("--verify-live-host", action="store_true", help="re-probe and compare the bound host without a model call")
    parser.add_argument("--execute", action="store_true", help="perform the model call and write capture artifacts")
    parser.add_argument("--acknowledge-cost", action="store_true", help="confirm the bounded model call may consume quota or money")
    args = parser.parse_args()
    if sum((args.print_command, args.verify_live_host, args.execute)) != 1:
        parser.error("choose exactly one of --print-command, --verify-live-host, or --execute")
    if args.execute and not args.acknowledge_cost:
        parser.error("--execute requires --acknowledge-cost")
    try:
        job = regular_input_file(args.job)
        if job is None: raise ValueError("job must be a regular file, not a symlink")
        data = json.loads(job.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"cannot read job: {exc}", file=sys.stderr)
        return 2
    root = Path.cwd().resolve()
    errors = validate_job(data, root, args.execute or args.verify_live_host)
    if errors:
        print("skill eval capture job invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    if args.print_command:
        placeholder = (root / data["output_dir"] / "final.md").resolve()
        print(json.dumps({"ok": True, "host": data["host"], "argv": command_for(data, root, placeholder)}, indent=2))
        return 0
    if args.verify_live_host:
        ok, reason = verify_live_host(data, root)
        print(json.dumps({"ok": ok, "host": data["host"], "reason": reason}, indent=2))
        return 0 if ok else 2
    return execute(data, root, args.job)


if __name__ == "__main__":
    raise SystemExit(main())
