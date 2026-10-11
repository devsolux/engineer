#!/usr/bin/env python3
"""Prepare a complete sealed Codex/Claude baseline batch without spending quota."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file

LIMITATIONS = [
    "The manifest is the batch commit marker; job files without a valid manifest are incomplete.",
    "Atomic replacement applies per file, not as a filesystem-wide transaction.",
    "Preparation proves local compilation and coverage, not provider execution, authorization, or behavior.",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_compiler(root: Path) -> Any:
    sys.dont_write_bytecode = True
    path = root / "scripts" / "capture-skill-eval.py"
    spec = importlib.util.spec_from_file_location("engineer_capture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load capture compiler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_temp(directory: Path, name: str, body: bytes) -> Path:
    handle, raw_path = tempfile.mkstemp(prefix=f".{name}.", suffix=".tmp", dir=directory)
    path = Path(raw_path)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def job_payload(compiler: Any, root: Path, inventory_path: Path, item: dict[str, Any], host: str, scenario_id: int, activation_mode: str, version: str, evals: Path) -> dict[str, Any]:
    run_id = f"engineer-v{version.replace('.', '-')}-{host}-{activation_mode}-s{scenario_id}"
    return {
        "schema_version": 5,
        "run_kind": "captured_run",
        "run_id": run_id,
        "host": host,
        "host_inventory": {
            "path": inventory_path.relative_to(root).as_posix(), "sha256": digest(inventory_path), "host": host,
            "executable_sha256": item["executable_sha256"], "version_output_sha256": item["version_output_sha256"],
            "help_output_sha256": item["help_output_sha256"], "required_capabilities": compiler.HOST_REQUIRED_CAPABILITIES[host],
        },
        "authentication": {"mode": "api_key_env", "api_key_env": "CODEX_API_KEY" if host == "codex" else "ANTHROPIC_API_KEY", "isolated_home": True, "cached_credentials_allowed": False, "keyring_allowed": False},
        "skill_bundle": {"source_root": ".", "sha256": compiler.bundle_sha256(root), "version": version, "include": list(compiler.BUNDLE_INCLUDE), "exclude_prefixes": list(compiler.BUNDLE_EXCLUDE_PREFIXES), "expectations_excluded": True},
        "model": "default",
        "scenario": {
            "id": scenario_id,
            "activation_mode": activation_mode,
            "invocation": ("$engineer" if host == "codex" else "/engineer-eval:engineer") if activation_mode == "explicit" else None,
            "activation_probe": {"request": compiler.ACTIVATION_PROBE_REQUEST, "response_sha256": compiler.ACTIVATION_PROBE_SHA256},
            "source_path": "evals/evals.json", "source_sha256": digest(evals), "expectations_exposed": False,
        },
        "workspace": "templates/fixtures/skill-eval/workspace", "fixture_marker": ".engineer-eval-fixture",
        "permissions": {"sandbox": "read_only", "network": "deny", "allowed_tools": ["Read", "Glob", "Grep"], "external_writes": False},
        "budgets": {"timeout_seconds": 300, "max_turns": 12, "max_cost_usd": 1.0},
        "output_dir": f".engineer/eval-captures/{run_id}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--scenarios", default="121", help="comma-separated keyword-free public smoke scenario IDs; keep private holdouts outside git")
    parser.add_argument("--hosts", default="codex,claude")
    parser.add_argument("--activation-modes", default="explicit,implicit", help="comma-separated control and auto-routing arms")
    parser.add_argument("--inventory", type=Path, help="existing repository-confined validated inventory; otherwise capture live")
    parser.add_argument("--output-dir", type=Path, default=Path(".engineer/eval-jobs"))
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output_dir if args.output_dir.is_absolute() else root / args.output_dir).resolve()
    try:
        output.relative_to(root)
    except ValueError:
        print("output directory must stay inside the repository", file=sys.stderr)
        return 2
    output.mkdir(parents=True, exist_ok=True)
    lock_path = output / ".prepare.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        print("another preparation holds the output lock", file=sys.stderr)
        return 2
    os.close(lock_fd)
    staged: list[Path] = []
    try:
        inventory_path = regular_input_file(args.inventory) if args.inventory else output / "host-capabilities.json"
        if args.inventory and inventory_path is None:
            print("inventory must be a regular file, not a symlink", file=sys.stderr)
            return 2
        try:
            inventory_path.relative_to(root)
        except ValueError:
            print("inventory must stay inside the repository for job binding", file=sys.stderr)
            return 2
        if args.inventory is None:
            captured = subprocess.run([sys.executable, str(root / "scripts/capture-host-capabilities.py"), "--cwd", str(root)], capture_output=True)
            if captured.returncode != 0:
                return 2
            inventory_temp = write_temp(output, inventory_path.name, captured.stdout)
            staged.append(inventory_temp)
            os.replace(inventory_temp, inventory_path)
            staged.remove(inventory_temp)
        checked = subprocess.run([sys.executable, str(root / "scripts/validate-host-capabilities.py"), str(inventory_path)], capture_output=True)
        if checked.returncode != 0:
            print("host inventory invalid", file=sys.stderr)
            return 2
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        observed = {item["id"]: item for item in inventory["hosts"]}
        compiler = load_compiler(root)
        required = compiler.HOST_REQUIRED_CAPABILITIES
        evals = root / "evals" / "evals.json"
        try:
            scenarios = sorted(set(int(value) for value in args.scenarios.split(",") if value))
        except ValueError:
            scenarios = []
        hosts = sorted(set(value for value in args.hosts.split(",") if value))
        activation_modes = sorted(set(value for value in args.activation_modes.split(",") if value))
        if not scenarios or any(host not in required for host in hosts) or not activation_modes or any(mode not in {"explicit", "implicit"} for mode in activation_modes):
            print("scenarios, hosts, and explicit/implicit activation modes must be supported", file=sys.stderr)
            return 2
        for host in hosts:
            item = observed.get(host, {})
            if item.get("installed") is not True or not set(required[host]) <= set(item.get("capabilities", [])):
                print(f"host missing required reviewed surface: {host}", file=sys.stderr)
                return 2

        planned: list[tuple[Path, Path, dict[str, Any], bytes]] = []
        for host in hosts:
            for scenario_id in scenarios:
                for activation_mode in activation_modes:
                    job = job_payload(compiler, root, inventory_path, observed[host], host, scenario_id, activation_mode, compiler.VERSION_RE.search((root / "SKILL.md").read_text()).group(1), evals)
                    final_path = output / f"{job['run_id']}.json"
                    body = (json.dumps(job, indent=2) + "\n").encode()
                    if final_path.exists() and final_path.read_bytes() != body:
                        print(f"refusing to replace non-identical prepared job: {final_path}", file=sys.stderr)
                        return 2
                    temp_path = write_temp(output, final_path.name, body)
                    staged.append(temp_path)
                    valid = subprocess.run([sys.executable, str(root / "scripts/capture-skill-eval.py"), str(temp_path), "--print-command"], cwd=root, capture_output=True)
                    if valid.returncode != 0:
                        print(f"batch job failed canonical compilation: {final_path}", file=sys.stderr)
                        return 2
                    planned.append((temp_path, final_path, job, body))

        manifest_path = output / "manifest.json"
        manifest_path.unlink(missing_ok=True)
        for temp_path, final_path, _, _ in planned:
            os.replace(temp_path, final_path)
            staged.remove(temp_path)
        jobs = [{
            "path": final_path.relative_to(root).as_posix(), "sha256": digest(final_path), "run_id": job["run_id"],
            "host": job["host"], "activation_mode": job["scenario"]["activation_mode"], "scenario_id": job["scenario"]["id"],
            "api_key_present": bool(os.environ.get(job["authentication"]["api_key_env"])),
        } for _, final_path, job, _ in planned]
        manifest = {
            "schema_version": 1, "receipt_kind": "prepared_eval_batch",
            "prepared_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "inventory": {"path": inventory_path.relative_to(root).as_posix(), "sha256": digest(inventory_path)},
            "batch": {
                "skill_version": planned[0][2]["skill_bundle"]["version"], "skill_bundle_sha256": planned[0][2]["skill_bundle"]["sha256"],
                "scenario_source_sha256": digest(evals), "hosts": hosts, "activation_modes": activation_modes,
                "scenario_ids": scenarios, "job_count": len(jobs),
            },
            "jobs": jobs,
            "publication": {"state": "complete", "commit_marker": "manifest.json", "atomic_per_file": True, "collision_policy": "identical_only", "lock": "exclusive"},
            "limitations": LIMITATIONS,
        }
        manifest_temp = write_temp(output, manifest_path.name, (json.dumps(manifest, indent=2) + "\n").encode())
        staged.append(manifest_temp)
        valid_manifest = subprocess.run([sys.executable, str(root / "scripts/validate-skill-eval-batch.py"), str(manifest_temp), "--root", str(root)], cwd=root, capture_output=True)
        if valid_manifest.returncode != 0:
            print("prepared batch manifest failed validation", file=sys.stderr)
            return 2
        os.replace(manifest_temp, manifest_path)
        staged.remove(manifest_temp)
        print(json.dumps({"manifest": manifest_path.relative_to(root).as_posix(), "manifest_sha256": digest(manifest_path), "prepared": jobs, "executed": False, "quota_spent": False}, indent=2))
        return 0
    finally:
        for path in staged:
            path.unlink(missing_ok=True)
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
