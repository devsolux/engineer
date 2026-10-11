#!/usr/bin/env python3
"""Validate a hash-bound aggregate run of parallel browser evidence lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

HEX = set("0123456789abcdef")
MODES = {"public_read", "auth_read", "isolated_write", "shared_write"}
SCOPES = {"read_only", "fixture_owned", "shared_account_serial"}


def is_hash(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX


def timestamp(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None
    except ValueError:
        return None


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def overlaps(left: tuple[datetime, datetime], right: tuple[datetime, datetime]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def validate(data: Any, receipt_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    root = receipt_path.parent
    root_keys = {"schema_version", "run_kind", "run_id", "concurrency", "lanes", "review", "decision"}
    if not isinstance(data, dict):
        return ["root must be an object"], []
    if set(data) != root_keys:
        errors.append(f"root keys must be exactly {sorted(root_keys)}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("run_kind") not in {"illustrative_fixture", "captured_run"} or not isinstance(data.get("run_id"), str) or not data.get("run_id"):
        errors.append("run identity is invalid")

    concurrency = data.get("concurrency", {})
    concurrency_keys = {"max_parallel", "shared_write_max_parallel", "cross_lane_account_overlap", "artifact_roots_unique", "cleanup_required"}
    if not isinstance(concurrency, dict) or set(concurrency) != concurrency_keys:
        errors.append("concurrency keys invalid")
        concurrency = {}
    if not isinstance(concurrency.get("max_parallel"), int) or isinstance(concurrency.get("max_parallel"), bool) or concurrency.get("max_parallel", 0) < 1:
        errors.append("max_parallel must be a positive integer")
    if concurrency.get("shared_write_max_parallel") != 1 or concurrency.get("cross_lane_account_overlap") != "deny_when_any_lane_writes" or concurrency.get("artifact_roots_unique") is not True or concurrency.get("cleanup_required") is not True:
        gates.append("concurrency policy must serialize shared writes and isolate accounts, artifacts, and cleanup")

    lanes = data.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        errors.append("lanes must be a non-empty array")
        lanes = []
    lane_keys = {"id", "mode", "worker_id", "namespace", "account_id_sha256", "tenant_id_sha256", "mutation_scope", "artifact_root", "receipt_path", "receipt_sha256"}
    seen_ids: set[str] = set()
    seen_workers: set[str] = set()
    seen_namespaces: set[str] = set()
    seen_receipts: set[Path] = set()
    seen_artifact_roots: set[Path] = set()
    write_accounts: dict[str, tuple[str, str]] = {}
    write_tenants: dict[str, tuple[str, str]] = {}
    sessions: list[dict[str, Any]] = []
    canonical_validator = Path(__file__).with_name("validate-browser-session.py")

    for index, lane in enumerate(lanes):
        label = f"lane {index}"
        if not isinstance(lane, dict) or set(lane) != lane_keys:
            errors.append(f"{label} keys invalid")
            continue
        lane_id, mode = lane.get("id"), lane.get("mode")
        for field, seen in (("id", seen_ids), ("worker_id", seen_workers), ("namespace", seen_namespaces)):
            value = lane.get(field)
            if not isinstance(value, str) or not value or value in seen:
                gates.append(f"{label} {field} missing or not unique")
            else:
                seen.add(value)
        if mode not in MODES or lane.get("mutation_scope") not in SCOPES:
            errors.append(f"{label} mode or mutation scope invalid")
        expected_scope = {"public_read": "read_only", "auth_read": "read_only", "isolated_write": "fixture_owned", "shared_write": "shared_account_serial"}.get(mode)
        if lane.get("mutation_scope") != expected_scope:
            gates.append(f"{label} mutation scope does not match lane mode")
        account, tenant = lane.get("account_id_sha256"), lane.get("tenant_id_sha256")
        if mode == "public_read":
            if account is not None or tenant is not None:
                gates.append(f"{label} public lane must not declare account or tenant identity")
        elif not is_hash(account):
            gates.append(f"{label} authenticated lane requires a hashed account identity")
        if mode in {"isolated_write", "shared_write"}:
            if not is_hash(tenant):
                gates.append(f"{label} write lane requires a hashed tenant identity")
            if is_hash(account) and account in write_accounts and (mode == "isolated_write" or write_accounts[account][1] == "isolated_write"):
                gates.append(f"{label} reuses isolated write account from {write_accounts[account][0]}")
            elif is_hash(account):
                write_accounts[account] = (str(lane_id), str(mode))
            if is_hash(tenant) and tenant in write_tenants and (mode == "isolated_write" or write_tenants[tenant][1] == "isolated_write"):
                gates.append(f"{label} reuses isolated write tenant from {write_tenants[tenant][0]}")
            elif is_hash(tenant):
                write_tenants[tenant] = (str(lane_id), str(mode))

        session_path = safe_path(lane.get("receipt_path"), root)
        artifact_root = safe_path(lane.get("artifact_root"), root)
        if session_path is None or not session_path.is_file() or session_path in seen_receipts or not is_hash(lane.get("receipt_sha256")) or digest(session_path) != lane.get("receipt_sha256"):
            errors.append(f"{label} receipt path, uniqueness, or digest invalid")
            continue
        seen_receipts.add(session_path)
        if artifact_root is None or artifact_root in seen_artifact_roots:
            gates.append(f"{label} artifact root is unsafe or not unique")
        else:
            seen_artifact_roots.add(artifact_root)
        try:
            session = json.loads(session_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(f"{label} receipt JSON invalid")
            continue
        result = subprocess.run([sys.executable, str(canonical_validator), str(session_path), "--json"], capture_output=True, text=True, timeout=20, check=False)
        try:
            session_result = json.loads(result.stdout)
        except json.JSONDecodeError:
            session_result = {}
        if result.returncode != 0 or session_result.get("valid") is not True:
            gates.append(f"{label} fails canonical browser-session validation")
        identity = session.get("session", {})
        if identity.get("lane") != lane_id or identity.get("worker_id") != lane.get("worker_id") or identity.get("namespace") != lane.get("namespace"):
            gates.append(f"{label} aggregate identity differs from session receipt")
        if identity.get("account_id_sha256") != account or identity.get("tenant_id_sha256") != tenant:
            gates.append(f"{label} aggregate account or tenant identity differs from session receipt")
        expected_risk = {"public_read": "public_read", "auth_read": "auth_read", "isolated_write": "fixture_write", "shared_write": "fixture_write"}.get(mode)
        if identity.get("risk_class") != expected_risk:
            gates.append(f"{label} risk class differs from lane mode")
        storage = identity.get("storage_state", {})
        if mode != "public_read" and (storage.get("used") is not True or storage.get("shared_between_workers") is not False):
            gates.append(f"{label} authenticated storage is missing or shared")
        if mode == "public_read" and storage.get("used") is not False:
            gates.append(f"{label} public lane used authentication state")
        if artifact_root is not None:
            for artifact in session.get("artifacts", []) if isinstance(session.get("artifacts"), list) else []:
                artifact_path = safe_path(artifact.get("path"), session_path.parent) if isinstance(artifact, dict) else None
                try:
                    if artifact_path is None:
                        raise ValueError
                    artifact_path.relative_to(artifact_root)
                except ValueError:
                    gates.append(f"{label} artifact escapes its unique root")
        start, end = timestamp(identity.get("started_at")), timestamp(identity.get("ended_at"))
        sessions.append({"id": lane_id, "mode": mode, "account": account, "interval": (start, end), "receipt": session})

    for left_index, left in enumerate(sessions):
        for right in sessions[left_index + 1:]:
            if left["mode"] == right["mode"] == "shared_write" and all(left["interval"]) and all(right["interval"]) and overlaps(left["interval"], right["interval"]):
                gates.append(f"shared-write lanes {left['id']} and {right['id']} overlap")
            if left["account"] is not None and left["account"] == right["account"] and ({left["mode"], right["mode"]} & {"isolated_write", "shared_write"}):
                if all(left["interval"]) and all(right["interval"]) and overlaps(left["interval"], right["interval"]):
                    gates.append(f"lanes {left['id']} and {right['id']} overlap on an account while one writes")
    events: list[tuple[datetime, int]] = []
    for item in sessions:
        if all(item["interval"]):
            events.extend([(item["interval"][0], 1), (item["interval"][1], -1)])
    active = peak = 0
    for _, delta in sorted(events, key=lambda item: (item[0], item[1])):
        active += delta
        peak = max(peak, active)
    if peak > concurrency.get("max_parallel", 0):
        gates.append(f"observed parallelism {peak} exceeds declared max_parallel")

    review = data.get("review", {})
    if not isinstance(review, dict) or set(review) != {"reviewer", "all_sessions_reviewed", "isolation_reviewed", "cleanup_reviewed", "approved", "notes"} or not isinstance(review.get("reviewer"), str) or not review.get("reviewer") or any(review.get(key) is not True for key in ("all_sessions_reviewed", "isolation_reviewed", "cleanup_reviewed")) or not isinstance(review.get("approved"), bool) or not isinstance(review.get("notes"), str) or not review.get("notes"):
        gates.append("aggregate review invalid")
        review = {}
    session_reviewers = {item["receipt"].get("review", {}).get("reviewer") for item in sessions}
    if review.get("reviewer") in session_reviewers:
        gates.append("aggregate reviewer must be independent from session reviewers")

    decision = data.get("decision", {})
    if not isinstance(decision, dict) or set(decision) != {"outcome", "reasons", "unresolved_risks"} or decision.get("outcome") not in {"pass", "fail", "infrastructure_error"} or not isinstance(decision.get("reasons"), list) or not decision.get("reasons") or not isinstance(decision.get("unresolved_risks"), list):
        errors.append("decision invalid")
        decision = {}
    if decision.get("outcome") == "pass":
        if data.get("run_kind") != "captured_run" or review.get("approved") is not True or decision.get("unresolved_risks"):
            gates.append("passing lane run requires captured evidence, approval, and no unresolved risks")
        if any(item["receipt"].get("receipt_kind") != "captured_session" or item["receipt"].get("decision", {}).get("outcome") != "pass" for item in sessions):
            gates.append("every lane must contain a passing captured browser session")
    return errors, gates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    path = regular_input_file(args.receipt)
    if path is None:
        print("receipt must be a regular file, not a symlink", file=sys.stderr)
        return 2
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    errors, gates = validate(data, path)
    valid = not errors and not gates
    output = {"valid": valid, "errors": errors, "gates": gates}
    print(json.dumps(output, indent=2) if args.json else ("browser lane run valid" if valid else "\n".join([*(f"error: {item}" for item in errors), *(f"gate: {item}" for item in gates)])))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
