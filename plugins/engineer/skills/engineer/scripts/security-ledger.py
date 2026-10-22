#!/usr/bin/env python3
"""Maintain an Engineer security-audit coverage ledger (coverage.json).

This is the parent's trusted code for the shared ledger. Hunters, critics and
verifiers never write it; the parent promotes their result files through here.

Subcommands:
  init     build a ledger: every surface x boundary x subsystem x attack-class
           cell becomes one ``planned`` unit with a derived coverage id
  assign   open or extend a hunting wave and hand units to one hunter
  promote  merge one hunter result (``--agent`` and ``--wave`` name the
           assignment; the file carries exactly units, candidates, hardening
           and uncovered) after regular-file, size (2 MiB), JSON,
           content-screen and assigned-unit checks; the result is copied to
           ``agents/<agent-id>.json`` beside the ledger, never overwritten
  gap      carry a prior run forward: ``carried_from`` on every shared unit,
           ``source_changed`` from ``git diff --name-only <prior ref>..HEAD``
           (reported as not possible, and treated as changed, without git)
  finish   close the run as complete, or incomplete with a reason

Every write validates the candidate ledger with validate-security-coverage.py
and replaces the file only when it is valid. The tool reads and writes JSON and
asks git for file names; it never executes target code. Profiles never relax a
rule. Exit 0 ok, 1 refused, 2 unreadable or unsafe input.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import create_new_bytes, regular_input_file, safe_path


def load_sibling(stem: str):
    path = Path(__file__).resolve().with_name(f"{stem}.py")
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


coverage_rules = load_sibling("validate-security-coverage")
findings_rules = load_sibling("validate-security-findings")
VALIDATOR = Path(__file__).resolve().with_name("validate-security-coverage.py")
ATTACK_CLASS_ORDER = ["injection", "access_control", "resource_handling", "crypto_secrets", "business_logic", "feature_abuse", "chained_trust", "wildcard"]
RESULT_STATUSES = {"covered", "candidate", "blocked", "deferred", "not_applicable", "out_of_scope"}
CARRY_STATUSES = {"covered", "candidate", "blocked", "deferred", "not_applicable", "out_of_scope"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
MAX_RESULT_BYTES = 2 * 1024 * 1024
MAX_LEDGER_BYTES = 8 * 1024 * 1024


class Refused(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def read_json(value: str, label: str, limit: int) -> tuple[Path, bytes, dict[str, Any]]:
    path = regular_input_file(value)
    if path is None:
        raise Refused(f"{label} must be a regular file, not a symlink", 2)
    if path.stat().st_size > limit:
        raise Refused(f"{label} exceeds {limit} bytes", 2)
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refused(f"{label} is not valid JSON: {exc}", 2) from None
    if not isinstance(data, dict):
        raise Refused(f"{label} must be a JSON object", 2)
    return path, raw, data


def load_ledger(value: str) -> tuple[Path, dict[str, Any]]:
    path, _, data = read_json(value, "ledger", MAX_LEDGER_BYTES)
    if not isinstance(data.get("units"), list) or not isinstance(data.get("waves"), list) or not isinstance(data.get("run"), dict) or not isinstance(data.get("dimensions"), dict):
        raise Refused("ledger lacks run, dimensions, units, or waves", 2)
    return path, data


def summarize(data: dict[str, Any]) -> None:
    dims = data["dimensions"]
    expected = 1
    for key in ("surfaces", "boundaries", "subsystems", "attack_classes"):
        expected *= len(dims.get(key, []))
    counts = {status: 0 for status in sorted(coverage_rules.UNIT_STATUS)}
    for unit in data["units"]:
        status = unit.get("status", "planned")
        counts[status] = counts.get(status, 0) + 1
    data["summary"] = {"expected_cells": expected, "units": len(data["units"]), "by_status": counts}


def validate_file(path: Path, evidence_root: Path, target_root: Path | None) -> tuple[bool, list[str]]:
    command = [sys.executable, str(VALIDATOR), str(path), "--evidence-root", str(evidence_root), "--json"]
    if target_root is not None:
        command += ["--target-root", str(target_root)]
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        report = json.loads(run.stdout)
    except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
        return False, [f"coverage validator did not complete: {exc}"]
    return run.returncode == 0 and report.get("valid") is True, [*report.get("errors", []), *report.get("gates", [])]


def write_ledger(path: Path, data: dict[str, Any], evidence_root: Path, target_root: Path | None) -> None:
    summarize(data)
    body = (json.dumps(data, indent=2) + "\n").encode("utf-8")
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    create_new_bytes(temp, body)
    try:
        ok, details = validate_file(temp, evidence_root, target_root)
        if not ok:
            raise Refused("ledger would be invalid; nothing written:\n" + "\n".join(f"- {item}" for item in details[:20]))
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def unit_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {unit["coverage_id"]: unit for unit in data["units"] if isinstance(unit, dict) and isinstance(unit.get("coverage_id"), str)}


def screen(label: str, body: str) -> list[str]:
    problems = []
    if findings_rules.FORBIDDEN_CONTENT.search(body):
        problems.append(f"{label} contains credential-shaped material")
    hosts = sorted({match.group(1) for match in findings_rules.URL.finditer(body) if not findings_rules.host_allowed(match.group(1))})
    if hosts:
        problems.append(f"{label} references non-fixture hosts: {hosts[:5]}")
    return problems


def resolve_roots(args: argparse.Namespace, ledger: Path) -> tuple[Path, Path | None]:
    evidence_root = Path(args.evidence_root) if args.evidence_root else ledger.parent
    target_root = Path(args.target_root) if args.target_root else None
    return evidence_root, target_root


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def command_init(args: argparse.Namespace) -> int:
    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise Refused(f"refusing to overwrite {output}")
    evidence_root = Path(args.evidence_root) if args.evidence_root else output.parent
    target_root = Path(args.target_root) if args.target_root else None
    _, _, dims = read_json(args.dimensions, "dimensions", MAX_LEDGER_BYTES)
    dims.setdefault("attack_classes", list(ATTACK_CLASS_ORDER))
    unknown = set(dims) - {"surfaces", "boundaries", "subsystems", "attack_classes"}
    if unknown:
        raise Refused(f"dimensions carry unknown keys: {sorted(unknown)}")
    architecture = safe_path(args.architecture, evidence_root)
    if architecture is None or not architecture.is_file():
        raise Refused("architecture brief must be a regular file under the evidence root", 2)
    digest = hashlib.sha256(architecture.read_bytes()).hexdigest()
    source_ref = args.source_ref
    if source_ref is None:
        git = shutil.which("git")
        if git is not None:
            try:
                run = subprocess.run([git, "-C", str(target_root or Path(".")), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30, check=False)
                head = run.stdout.strip()
                source_ref = head if run.returncode == 0 and HEX40.fullmatch(head) else None
            except (subprocess.TimeoutExpired, OSError):
                source_ref = None
    if source_ref is None:
        if args.receipt_kind == "captured_run":
            raise Refused("captured runs need --source-ref (40-hex) or a git repository at the target root")
        source_ref = "unknown"
    units = []
    for surface in dims.get("surfaces", []):
        for boundary in dims.get("boundaries", []):
            for subsystem in dims.get("subsystems", []):
                for attack_class in dims.get("attack_classes", []):
                    ids = (surface.get("id"), boundary.get("id"), subsystem.get("id"), attack_class)
                    if any(not isinstance(item, str) for item in ids):
                        raise Refused("every dimension entry needs a string id")
                    units.append({"coverage_id": coverage_rules.coverage_id(*ids), "surface": ids[0], "boundary": ids[1], "subsystem": ids[2], "attack_class": ids[3], "status": "planned", "owner": None, "wave": None, "reviewed_paths": [], "checks": [], "unresolved_reason": None, "candidate_fingerprints": [], "proposed_by": None, "carried_from": None})
    data = {
        "schema_version": 1,
        "receipt_kind": args.receipt_kind,
        "run": {
            "run_id": args.run_id,
            "target": {"name": args.target_name, "source_ref": source_ref, "root": args.target_root or "."},
            "profile": args.profile,
            "status": "incomplete",
            "incomplete_reason": "ledger initialized; no hunting wave has run",
            "prior_runs": list(dict.fromkeys(args.prior_run)),
            "sandbox": {"available": args.sandbox_unavailable is None, "unavailable_reason": args.sandbox_unavailable},
            "architecture": {"path": args.architecture, "sha256": digest},
        },
        "dimensions": dims,
        "units": units,
        "waves": [],
        "summary": {},
    }
    write_ledger(output, data, evidence_root, target_root)
    return emit({"ok": True, "action": "init", "ledger": str(output), "units": len(units), "source_ref": source_ref})


def command_assign(args: argparse.Namespace) -> int:
    ledger, data = load_ledger(args.ledger)
    evidence_root, target_root = resolve_roots(args, ledger)
    if args.wave < 1:
        raise Refused("wave numbers start at 1")
    if args.hunter == args.critic:
        raise Refused("the critic of a wave must not hunt in it")
    wave = next((item for item in data["waves"] if item.get("wave") == args.wave), None)
    if wave is None:
        wave = {"wave": args.wave, "hunters": [], "critic": args.critic, "units": []}
        data["waves"].append(wave)
        data["waves"].sort(key=lambda item: item.get("wave", 0))
    elif wave.get("critic") != args.critic:
        raise Refused(f"wave {args.wave} already has critic {wave.get('critic')}")
    if args.critic in wave["hunters"]:
        raise Refused("the critic of a wave must not hunt in it")
    if args.hunter not in wave["hunters"]:
        wave["hunters"].append(args.hunter)
    units = unit_index(data)
    for cid in args.units:
        unit = units.get(cid)
        if unit is None:
            raise Refused(f"unknown coverage unit {cid}")
        if unit.get("status") not in {"planned", "blocked", "deferred"}:
            raise Refused(f"unit {cid} is {unit.get('status')}; only planned, blocked, or deferred units can be assigned")
        unit.update({"status": "in_progress", "owner": args.hunter, "wave": args.wave, "unresolved_reason": None, "reviewed_paths": [], "checks": [], "candidate_fingerprints": []})
        if cid not in wave["units"]:
            wave["units"].append(cid)
    if data["run"].get("status") == "complete":
        data["run"]["status"] = "incomplete"
        data["run"]["incomplete_reason"] = f"hunting wave {args.wave} in progress"
    write_ledger(ledger, data, evidence_root, target_root)
    return emit({"ok": True, "action": "assign", "wave": args.wave, "hunter": args.hunter, "units": list(args.units)})


def command_promote(args: argparse.Namespace) -> int:
    ledger, data = load_ledger(args.ledger)
    evidence_root, target_root = resolve_roots(args, ledger)
    agent, wave_number = args.agent, args.wave
    if not coverage_rules.agent(agent) or wave_number < 1:
        raise Refused("--agent must be an agent id and --wave a positive integer")
    _, raw, result = read_json(args.result, "agent result", MAX_RESULT_BYTES)
    if set(result) != {"units", "candidates", "hardening", "uncovered"}:
        raise Refused("agent result must carry exactly units, candidates, hardening, and uncovered")
    problems = screen("agent result", raw.decode("utf-8", errors="replace"))
    wave = next((item for item in data["waves"] if item.get("wave") == wave_number), None)
    if wave is None or agent not in wave.get("hunters", []):
        raise Refused(f"agent {agent} is not a hunter of wave {wave_number}")
    units = unit_index(data)
    assigned = {cid for cid, unit in units.items() if unit.get("owner") == agent and unit.get("wave") == wave_number and unit.get("status") == "in_progress"}
    candidates: dict[str, dict[str, Any]] = {}
    for index, candidate in enumerate(result["candidates"] if isinstance(result["candidates"], list) else []):
        root_cause = candidate.get("root_cause") if isinstance(candidate, dict) else None
        if not isinstance(candidate, dict) or not isinstance(root_cause, dict) or candidate.get("attack_class") not in coverage_rules.ATTACK_CLASSES or not text(root_cause.get("path")):
            problems.append(f"candidate {index} lacks an attack_class and root_cause.path")
            continue
        expected = findings_rules.fingerprint(candidate["attack_class"], root_cause["path"], root_cause.get("symbol"), root_cause.get("sink"))
        if candidate.get("fingerprint") != expected:
            problems.append(f"candidate {index} fingerprint does not match its root cause (expected {expected})")
            continue
        ids = candidate.get("coverage_ids")
        if not isinstance(ids, list) or not ids or any(cid not in assigned for cid in ids):
            problems.append(f"candidate {expected} references units not assigned to {agent} in wave {wave_number}")
            continue
        candidates[expected] = candidate
    seen: set[str] = set()
    merged: list[tuple[str, dict[str, Any]]] = []
    for index, unit in enumerate(result["units"] if isinstance(result["units"], list) else []):
        if not isinstance(unit, dict) or set(unit) != {"coverage_id", "status", "reviewed_paths", "checks", "unresolved_reason", "candidate_fingerprints"}:
            problems.append(f"result unit {index} shape invalid")
            continue
        cid = unit["coverage_id"]
        if cid not in assigned:
            problems.append(f"unit {cid} is not assigned to {agent} in wave {wave_number}")
            continue
        if cid in seen:
            problems.append(f"unit {cid} reported twice")
            continue
        seen.add(cid)
        if unit.get("status") not in RESULT_STATUSES:
            problems.append(f"unit {cid} status must be one of {sorted(RESULT_STATUSES)}")
            continue
        fingerprints = unit.get("candidate_fingerprints")
        if not isinstance(fingerprints, list) or any(fp not in candidates or cid not in candidates[fp].get("coverage_ids", []) for fp in fingerprints):
            problems.append(f"unit {cid} lists candidate fingerprints without a matching candidate")
            continue
        merged.append((cid, unit))
    blocked: list[tuple[str, str]] = []
    gaps: list[str] = []
    for index, item in enumerate(result["uncovered"] if isinstance(result["uncovered"], list) else []):
        if not isinstance(item, dict) or set(item) != {"coverage_id", "description"} or not text(item.get("description")):
            problems.append(f"uncovered {index} must carry coverage_id (null for an observed gap) and description")
            continue
        cid = item["coverage_id"]
        if cid is None:
            gaps.append(item["description"])
            continue
        if cid not in assigned or cid in seen:
            problems.append(f"uncovered unit {cid} is not an assigned unit awaiting a result")
            continue
        seen.add(cid)
        blocked.append((cid, item["description"]))
    if not isinstance(result["hardening"], list):
        problems.append("hardening must be a list")
    if problems:
        raise Refused("agent result refused:\n" + "\n".join(f"- {item}" for item in problems[:20]))
    agents_dir = ledger.parent / "agents"
    agents_dir.mkdir(exist_ok=True)
    destination = agents_dir / f"{agent}.json"
    if destination.exists() or destination.is_symlink():
        raise Refused(f"{destination} already exists; agent ids are unique per run")
    for cid, unit in merged:
        units[cid].update({"status": unit["status"], "reviewed_paths": unit["reviewed_paths"], "checks": unit["checks"], "unresolved_reason": unit["unresolved_reason"], "candidate_fingerprints": unit["candidate_fingerprints"]})
    for cid, reason in blocked:
        units[cid].update({"status": "blocked", "reviewed_paths": [], "checks": [], "unresolved_reason": reason, "candidate_fingerprints": []})
    create_new_bytes(destination, raw)
    try:
        write_ledger(ledger, data, evidence_root, target_root)
    except Refused:
        destination.unlink()
        raise
    counts: dict[str, int] = {}
    for cid in seen:
        counts[units[cid]["status"]] = counts.get(units[cid]["status"], 0) + 1
    return emit({"ok": True, "action": "promote", "agent": agent, "wave": wave_number, "units": counts, "candidates": sorted(candidates), "unaccounted": sorted(assigned - seen), "observed_gaps": gaps, "copied_to": str(destination)})


def changed_files(target_root: Path, source_ref: Any) -> tuple[set[str] | None, str]:
    suffix = "source change check not possible; every shared unit is treated as changed"
    if not isinstance(source_ref, str) or not HEX40.fullmatch(source_ref):
        return None, f"prior source_ref is not a commit hash; {suffix}"
    git = shutil.which("git")
    if git is None:
        return None, f"git is not available; {suffix}"
    try:
        run = subprocess.run([git, "-C", str(target_root), "diff", "--name-only", "--relative", f"{source_ref}..HEAD"], capture_output=True, text=True, timeout=60, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, f"git diff failed ({exc}); {suffix}"
    if run.returncode != 0:
        return None, f"git diff failed ({run.stderr.strip()[:160] or 'not a git repository'}); {suffix}"
    changed = {line.strip() for line in run.stdout.splitlines() if line.strip()}
    return changed, f"compared {source_ref[:12]}..HEAD under {target_root}: {len(changed)} changed file(s)"


def touched(prefixes: list[str], changed: set[str] | None) -> bool:
    if changed is None:
        return True
    cleaned = [prefix.strip("/") for prefix in prefixes if text(prefix)]
    return any(path == prefix or path.startswith(prefix + "/") for path in changed for prefix in cleaned)


def command_gap(args: argparse.Namespace) -> int:
    ledger, data = load_ledger(args.ledger)
    evidence_root, target_root = resolve_roots(args, ledger)
    prior_dir = Path(args.prior)
    if prior_dir.is_symlink():
        raise Refused("prior run directory must not be a symlink", 2)
    _, _, prior = read_json(str(prior_dir / "coverage.json"), "prior ledger", MAX_LEDGER_BYTES)
    prior_run = prior.get("run") if isinstance(prior.get("run"), dict) else {}
    prior_id = prior_run.get("run_id")
    if not isinstance(prior_id, str) or not coverage_rules.RUN_ID.fullmatch(prior_id) or prior_id == data["run"].get("run_id"):
        raise Refused("prior ledger must carry a different valid run_id")
    if prior_id not in data["run"].setdefault("prior_runs", []):
        data["run"]["prior_runs"].append(prior_id)
    prior_target = prior_run.get("target") if isinstance(prior_run.get("target"), dict) else {}
    changed, note = changed_files(target_root or Path("."), prior_target.get("source_ref"))
    subsystem_paths = {row.get("id"): row.get("paths", []) for row in data["dimensions"].get("subsystems", []) if isinstance(row, dict)}
    prior_units = {unit.get("coverage_id"): unit for unit in prior.get("units", []) if isinstance(unit, dict)}
    stats = {"shared": 0, "source_changed": 0, "carried": 0}
    for unit in data["units"]:
        prior_unit = prior_units.get(unit.get("coverage_id"))
        if prior_unit is None:
            continue
        stats["shared"] += 1
        prefixes = [*subsystem_paths.get(unit.get("subsystem"), []), *prior_unit.get("reviewed_paths", []), *(path for check in prior_unit.get("checks", []) if isinstance(check, dict) for path in check.get("paths", []))]
        source_changed = touched(prefixes, changed)
        prior_status = prior_unit.get("status") if prior_unit.get("status") in coverage_rules.UNIT_STATUS else "planned"
        unit["carried_from"] = {"run_id": prior_id, "prior_status": prior_status, "source_changed": source_changed}
        if source_changed:
            stats["source_changed"] += 1
        elif unit.get("status") == "planned" and prior_status in CARRY_STATUSES:
            unit.update({"status": prior_status, "owner": None, "wave": None, "proposed_by": None, "reviewed_paths": list(prior_unit.get("reviewed_paths", [])), "checks": list(prior_unit.get("checks", [])), "unresolved_reason": prior_unit.get("unresolved_reason"), "candidate_fingerprints": list(prior_unit.get("candidate_fingerprints", []))})
            stats["carried"] += 1
    write_ledger(ledger, data, evidence_root, target_root)
    return emit({"ok": True, "action": "gap", "prior_run": prior_id, "source_check": note, **stats, "prior_only_units": len(set(prior_units) - set(unit_index(data)))})


def command_finish(args: argparse.Namespace) -> int:
    ledger, data = load_ledger(args.ledger)
    evidence_root, target_root = resolve_roots(args, ledger)
    if args.incomplete is not None and not text(args.incomplete):
        raise Refused("--incomplete needs a non-empty reason")
    data["run"]["status"] = "incomplete" if args.incomplete is not None else "complete"
    data["run"]["incomplete_reason"] = args.incomplete
    write_ledger(ledger, data, evidence_root, target_root)
    return emit({"ok": True, "action": "finish", "status": data["run"]["status"], "incomplete_reason": args.incomplete})


def main() -> int:
    parser = argparse.ArgumentParser(description="Maintain a security-audit coverage ledger.")
    commands = parser.add_subparsers(dest="command", required=True)

    def roots(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--evidence-root", default=None, help="root for the architecture binding (default: the ledger directory)")
        sub.add_argument("--target-root", default=None, help="target checkout; when given, document paths must exist under it")

    init = commands.add_parser("init", help="build a ledger from a dimensions file")
    init.add_argument("--dimensions", required=True)
    init.add_argument("--run-id", required=True)
    init.add_argument("--target-name", required=True)
    init.add_argument("--source-ref", default=None)
    init.add_argument("--profile", choices=sorted(coverage_rules.PROFILES), default="standard")
    init.add_argument("--architecture", required=True, help="architecture brief path relative to the evidence root")
    init.add_argument("--prior-run", action="append", default=[])
    init.add_argument("--sandbox-unavailable", default=None, metavar="REASON")
    init.add_argument("--receipt-kind", choices=sorted(coverage_rules.RECEIPT_KINDS), default="captured_run")
    init.add_argument("--output", required=True)
    roots(init)
    init.set_defaults(handler=command_init)

    assign = commands.add_parser("assign", help="hand planned units to a hunter inside a wave")
    assign.add_argument("ledger")
    assign.add_argument("--wave", type=int, required=True)
    assign.add_argument("--hunter", required=True)
    assign.add_argument("--critic", required=True)
    assign.add_argument("units", nargs="+")
    roots(assign)
    assign.set_defaults(handler=command_assign)

    promote = commands.add_parser("promote", help="merge one hunter result into the ledger")
    promote.add_argument("ledger")
    promote.add_argument("result")
    promote.add_argument("--agent", required=True, help="hunter id the result belongs to")
    promote.add_argument("--wave", type=int, required=True, help="wave the hunter was assigned in")
    roots(promote)
    promote.set_defaults(handler=command_promote)

    gap = commands.add_parser("gap", help="carry a prior run forward and mark changed source")
    gap.add_argument("ledger")
    gap.add_argument("--prior", required=True, metavar="RUN_DIR")
    roots(gap)
    gap.set_defaults(handler=command_gap)

    finish = commands.add_parser("finish", help="close the run")
    finish.add_argument("ledger")
    finish.add_argument("--incomplete", default=None, metavar="REASON")
    roots(finish)
    finish.set_defaults(handler=command_finish)

    args = parser.parse_args()
    try:
        return args.handler(args)
    except Refused as exc:
        print(f"security-ledger {args.command}: {exc}", file=sys.stderr)
        return exc.code
    except OSError as exc:
        print(f"security-ledger {args.command}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
