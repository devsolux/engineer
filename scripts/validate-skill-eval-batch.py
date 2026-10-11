#!/usr/bin/env python3
"""Validate a completely published, hash-bound skill-evaluation job batch."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

HEX = set("0123456789abcdef")
HOSTS = {"codex", "claude"}
MODES = {"explicit", "implicit"}
LIMITATIONS = {
    "The manifest is the batch commit marker; job files without a valid manifest are incomplete.",
    "Atomic replacement applies per file, not as a filesystem-wide transaction.",
    "Preparation proves local compilation and coverage, not provider execution, authorization, or behavior.",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def safe_file(value: Any, root: Path) -> Path | None:
    path = safe_path(value, root)
    return path if path is not None and path.is_file() else None


def validate(data: Any, root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    root_keys = {"schema_version", "receipt_kind", "prepared_at", "inventory", "batch", "jobs", "publication", "limitations"}
    if not isinstance(data, dict):
        return ["root must be an object"], []
    if set(data) != root_keys:
        errors.append("root keys invalid")
    if data.get("schema_version") != 1 or data.get("receipt_kind") != "prepared_eval_batch":
        errors.append("schema or receipt kind invalid")
    if not isinstance(data.get("prepared_at"), str) or not data.get("prepared_at", "").endswith("Z"):
        errors.append("prepared_at invalid")

    inventory = data.get("inventory", {})
    if not isinstance(inventory, dict) or set(inventory) != {"path", "sha256"}:
        errors.append("inventory binding invalid")
        inventory_path = None
    else:
        inventory_path = safe_file(inventory.get("path"), root)
        if inventory_path is None or not is_hash(inventory.get("sha256")) or digest(inventory_path) != inventory.get("sha256"):
            gates.append("inventory path or digest mismatch")
        elif subprocess.run([sys.executable, str(root / "scripts/validate-host-capabilities.py"), str(inventory_path)], capture_output=True).returncode != 0:
            gates.append("inventory fails canonical validation")

    batch = data.get("batch", {})
    batch_keys = {"skill_version", "skill_bundle_sha256", "scenario_source_sha256", "hosts", "activation_modes", "scenario_ids", "job_count"}
    if not isinstance(batch, dict) or set(batch) != batch_keys:
        errors.append("batch contract invalid")
        batch = {}
    hosts = batch.get("hosts")
    modes = batch.get("activation_modes")
    scenario_ids = batch.get("scenario_ids")
    if not isinstance(hosts, list) or not hosts or hosts != sorted(set(hosts)) or not set(hosts) <= HOSTS:
        errors.append("batch hosts invalid")
        hosts = []
    if not isinstance(modes, list) or not modes or modes != sorted(set(modes)) or not set(modes) <= MODES:
        errors.append("batch activation modes invalid")
        modes = []
    if not isinstance(scenario_ids, list) or not scenario_ids or scenario_ids != sorted(set(scenario_ids)) or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in scenario_ids):
        errors.append("batch scenario IDs invalid")
        scenario_ids = []
    expected = {(host, mode, scenario_id) for host in hosts for mode in modes for scenario_id in scenario_ids}
    if batch.get("job_count") != len(expected):
        gates.append("batch job_count does not match Cartesian coverage")
    if not isinstance(batch.get("skill_version"), str) or not batch.get("skill_version") or not is_hash(batch.get("skill_bundle_sha256")) or not is_hash(batch.get("scenario_source_sha256")):
        errors.append("batch skill or scenario binding invalid")

    jobs = data.get("jobs")
    observed: set[tuple[str, str, int]] = set()
    paths: set[str] = set()
    if not isinstance(jobs, list):
        errors.append("jobs must be an array")
        jobs = []
    for item in jobs:
        keys = {"path", "sha256", "run_id", "host", "activation_mode", "scenario_id", "api_key_present"}
        if not isinstance(item, dict) or set(item) != keys:
            errors.append("job entry invalid")
            continue
        host = item.get("host")
        mode = item.get("activation_mode")
        scenario_id = item.get("scenario_id")
        if host not in HOSTS or mode not in MODES or not isinstance(scenario_id, int) or isinstance(scenario_id, bool):
            errors.append("job identity invalid")
        else:
            identity = (host, mode, scenario_id)
            if identity in observed:
                gates.append("job identities must be unique")
            observed.add(identity)
        if type(item.get("api_key_present")) is not bool or not isinstance(item.get("run_id"), str) or not item.get("run_id"):
            errors.append("job metadata invalid")
        path_value = item.get("path")
        path = safe_file(path_value, root)
        if isinstance(path_value, str):
            if path_value in paths:
                gates.append("job paths must be unique")
            paths.add(path_value)
        if path is None or not is_hash(item.get("sha256")) or digest(path) != item.get("sha256"):
            gates.append("job path or digest mismatch")
            continue
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append("job cannot be parsed")
            continue
        if job.get("run_id") != item.get("run_id") or job.get("host") != item.get("host") or job.get("scenario", {}).get("activation_mode") != item.get("activation_mode") or job.get("scenario", {}).get("id") != item.get("scenario_id"):
            gates.append("job entry disagrees with job body")
        if job.get("skill_bundle", {}).get("version") != batch.get("skill_version") or job.get("skill_bundle", {}).get("sha256") != batch.get("skill_bundle_sha256") or job.get("scenario", {}).get("source_sha256") != batch.get("scenario_source_sha256"):
            gates.append("job body disagrees with batch binding")
        if inventory_path is not None and job.get("host_inventory", {}).get("path") != inventory.get("path"):
            gates.append("job inventory path disagrees with batch inventory")
        result = subprocess.run([sys.executable, str(root / "scripts/capture-skill-eval.py"), str(path), "--print-command"], cwd=root, capture_output=True)
        if result.returncode != 0:
            gates.append("job fails canonical compilation")
    if observed != expected or len(jobs) != len(expected):
        gates.append("published jobs do not exactly cover the declared Cartesian batch")

    publication = data.get("publication", {})
    if not isinstance(publication, dict) or publication != {"state": "complete", "commit_marker": "manifest.json", "atomic_per_file": True, "collision_policy": "identical_only", "lock": "exclusive"}:
        errors.append("publication policy invalid")
    if set(data.get("limitations", [])) != LIMITATIONS or len(data.get("limitations", [])) != 3:
        gates.append("mandatory limitations missing or altered")
    return errors, gates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    try:
        manifest = regular_input_file(args.manifest)
        if manifest is None: raise ValueError("manifest must be a regular file, not a symlink")
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors, gates = [str(exc)], []
    else:
        errors, gates = validate(data, root)
    if args.json:
        print(json.dumps({"ok": not errors and not gates, "errors": errors, "gates": gates}, indent=2))
    else:
        for message in errors:
            print(f"ERROR: {message}", file=sys.stderr)
        for message in gates:
            print(f"GATE: {message}", file=sys.stderr)
        if not errors and not gates:
            print("skill eval preparation batch valid")
    return 0 if not errors and not gates else 1


if __name__ == "__main__":
    raise SystemExit(main())
