#!/usr/bin/env python3
"""Validate an Engineer security-audit coverage ledger (coverage.json).

The ledger records which surface x boundary x subsystem x attack-class cells a
security audit examined, by whom, in which hunting wave, and with what result.
Identifiers are recomputed here and never trusted from the document:

    coverage_id = "cov-" + sha256("surface|boundary|subsystem|attack_class")[:12]

Paths inside the document are lexically confined and, when ``--target-root`` is
given, must exist under it. The architecture brief is bound by ``{path, sha256}``
relative to ``--evidence-root`` and must stay within 1000 words with all eight
``##`` headings. Profiles (quick, standard, deep) change hunting breadth only;
they never relax a rule in this validator.

``--json`` prints ``{"valid", "errors", "gates"}``. Exit 0 valid, 1 invalid,
2 unreadable input. Errors are shape or derivation faults; gates are policy or
consistency faults. Both block. Each list is capped at 100 entries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

ATTACK_CLASSES = {"injection", "access_control", "resource_handling", "crypto_secrets", "business_logic", "feature_abuse", "chained_trust", "wildcard"}
PROFILES = {"quick", "standard", "deep"}
RUN_STATUS = {"complete", "incomplete"}
RECEIPT_KINDS = {"illustrative_fixture", "captured_run"}
UNIT_STATUS = {"planned", "in_progress", "covered", "candidate", "blocked", "deferred", "out_of_scope", "not_applicable"}
SURFACE_KINDS = {"http", "ui", "cli", "job", "webhook", "rpc", "message", "file", "other"}
CHECK_METHODS = {"source", "local"}
ARCHITECTURE_HEADINGS = ("Principals", "Authority", "Protected resources", "Stack", "Entry surfaces", "Trust boundaries", "Starting paths", "Prior-run gaps")
AGENT_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
DIMENSION_ID = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
RUN_ID = re.compile(r"^run-[0-9]{3,}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX16 = re.compile(r"^[0-9a-f]{16}$")
FINGERPRINT = re.compile(r"^sa1-[0-9a-f]{16}$")
UNIT_KEYS = {"coverage_id", "surface", "boundary", "subsystem", "attack_class", "status", "owner", "wave", "reviewed_paths", "checks", "unresolved_reason", "candidate_fingerprints", "proposed_by", "carried_from"}
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_UNITS = 20000
MAX_WORDS = 1000
MAX_ITEMS = 100


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def optional_text(value: Any) -> bool:
    return value is None or text(value)


def obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def agent(value: Any) -> bool:
    return isinstance(value, str) and AGENT_ID.fullmatch(value) is not None


def coverage_id(surface: str, boundary: str, subsystem: str, attack_class: str) -> str:
    return "cov-" + hashlib.sha256(f"{surface}|{boundary}|{subsystem}|{attack_class}".encode()).hexdigest()[:12]


def lexical_path(value: Any) -> bool:
    if not text(value) or "\\" in value or "\0" in value or PureWindowsPath(value).drive:
        return False
    pure = PurePosixPath(value)
    return not pure.is_absolute() and ".." not in pure.parts


def target_path_ok(value: Any, target_root: Path | None) -> bool:
    if not lexical_path(value):
        return False
    if target_root is None:
        return True
    resolved = safe_path(value, target_root)
    return resolved is not None and resolved.exists()


def cap(items: list[str]) -> list[str]:
    if len(items) <= MAX_ITEMS:
        return items
    return items[: MAX_ITEMS - 1] + [f"{len(items) - MAX_ITEMS + 1} further item(s) suppressed"]


def check_architecture(binding: Any, root: Path, errors: list[str], gates: list[str]) -> None:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"} or not text(binding.get("path")) or not isinstance(binding.get("sha256"), str) or not HEX64.fullmatch(binding["sha256"]):
        errors.append("architecture binding must be {path, sha256}")
        return
    path = safe_path(binding["path"], root)
    if path is None or not path.is_file():
        gates.append("architecture artifact unavailable or unsafe")
        return
    try:
        raw = path.read_bytes()
    except OSError as exc:
        gates.append(f"architecture artifact unreadable: {exc}")
        return
    if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        gates.append("architecture artifact digest mismatch")
        return
    body = raw.decode("utf-8", errors="replace")
    words = len(body.split())
    if words > MAX_WORDS:
        gates.append(f"architecture brief has {words} words (max {MAX_WORDS})")
    headings = {line[3:].strip() for line in body.splitlines() if line.startswith("## ")}
    missing = [heading for heading in ARCHITECTURE_HEADINGS if heading not in headings]
    if missing:
        gates.append(f"architecture brief missing headings: {missing}")


def dimension_ids(rows: Any, label: str, keys: set[str], errors: list[str], check) -> list[str]:
    ids: list[str] = []
    if not isinstance(rows, list) or not rows:
        errors.append(f"dimensions.{label} must be a non-empty list")
        return ids
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != keys:
            errors.append(f"{label} {index} shape invalid")
            continue
        ident = row.get("id")
        if not isinstance(ident, str) or not DIMENSION_ID.fullmatch(ident):
            errors.append(f"{label} {index} id invalid")
            continue
        if ident in ids:
            errors.append(f"{label} id duplicated: {ident}")
            continue
        ids.append(ident)
        check(row, f"{label} {ident}")
    return ids


def validate(data: Any, evidence_root: Path, target_root: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"], []
    root_keys = {"schema_version", "receipt_kind", "run", "dimensions", "units", "waves", "summary"}
    if set(data) != root_keys:
        errors.append(f"root keys must be exactly {sorted(root_keys)}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    kind = data.get("receipt_kind")
    if kind not in RECEIPT_KINDS:
        errors.append("receipt_kind invalid")

    run = obj(data.get("run"))
    if set(run) != {"run_id", "target", "profile", "status", "incomplete_reason", "prior_runs", "sandbox", "architecture"}:
        errors.append("run shape invalid")
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        errors.append("run.run_id must match ^run-[0-9]{3,}$")
    target = obj(run.get("target"))
    if set(target) != {"name", "source_ref", "root"} or not all(text(target.get(key)) for key in ("name", "source_ref", "root")):
        errors.append("run.target must carry name, source_ref, and root")
    elif kind == "captured_run" and not HEX40.fullmatch(target["source_ref"]):
        errors.append("captured run requires a 40-hex source_ref")
    if run.get("profile") not in PROFILES:
        errors.append("run.profile must be quick, standard, or deep")
    run_status = run.get("status")
    if run_status not in RUN_STATUS:
        errors.append("run.status must be complete or incomplete")
    reason = run.get("incomplete_reason")
    if run_status == "incomplete" and not text(reason):
        errors.append("incomplete run requires a non-empty incomplete_reason")
    if run_status == "complete" and reason is not None:
        errors.append("complete run must carry a null incomplete_reason")
    prior = run.get("prior_runs")
    prior_ids: set[str] = set()
    if not isinstance(prior, list) or any(not isinstance(item, str) or not RUN_ID.fullmatch(item) for item in prior) or len(set(prior)) != len(prior) or run_id in prior:
        errors.append("run.prior_runs must be unique run ids excluding this run")
    else:
        prior_ids = set(prior)
    sandbox = obj(run.get("sandbox"))
    if set(sandbox) != {"available", "unavailable_reason"} or not isinstance(sandbox.get("available"), bool):
        errors.append("run.sandbox must carry available and unavailable_reason")
    elif sandbox["available"] and sandbox["unavailable_reason"] is not None:
        errors.append("available sandbox must carry a null unavailable_reason")
    elif not sandbox["available"] and not text(sandbox["unavailable_reason"]):
        errors.append("unavailable sandbox requires a reason")
    sandbox_available = sandbox.get("available") is True
    check_architecture(run.get("architecture"), evidence_root, errors, gates)

    dims = obj(data.get("dimensions"))
    if set(dims) != {"surfaces", "boundaries", "subsystems", "attack_classes"}:
        errors.append("dimensions must carry surfaces, boundaries, subsystems, and attack_classes")

    def surface_check(row: dict[str, Any], label: str) -> None:
        if not text(row.get("ref")) or row.get("kind") not in SURFACE_KINDS:
            errors.append(f"{label} needs a ref and a kind from {sorted(SURFACE_KINDS)}")

    def boundary_check(row: dict[str, Any], label: str) -> None:
        if not all(text(row.get(key)) for key in ("from", "to", "strongest_visible_control")):
            errors.append(f"{label} needs from, to, and strongest_visible_control")

    def subsystem_check(row: dict[str, Any], label: str) -> None:
        paths = row.get("paths")
        if not isinstance(paths, list) or not paths or any(not target_path_ok(item, target_root) for item in paths) or len(set(paths)) != len(paths):
            errors.append(f"{label} paths must be unique, lexically safe, and present under the target root")

    surfaces = dimension_ids(dims.get("surfaces"), "surface", {"id", "ref", "kind"}, errors, surface_check)
    boundaries = dimension_ids(dims.get("boundaries"), "boundary", {"id", "from", "to", "strongest_visible_control"}, errors, boundary_check)
    subsystems = dimension_ids(dims.get("subsystems"), "subsystem", {"id", "paths"}, errors, subsystem_check)
    classes = dims.get("attack_classes")
    if not isinstance(classes, list) or not classes or any(item not in ATTACK_CLASSES for item in classes) or len(set(classes)) != len(classes):
        errors.append(f"dimensions.attack_classes must be a unique non-empty subset of {sorted(ATTACK_CLASSES)}")
        classes = []

    waves = data.get("waves")
    wave_map: dict[int, dict[str, Any]] = {}
    critics: set[str] = set()
    if not isinstance(waves, list):
        errors.append("waves must be a list")
        waves = []
    for index, wave in enumerate(waves):
        if not isinstance(wave, dict) or set(wave) != {"wave", "hunters", "critic", "units"}:
            errors.append(f"wave {index} shape invalid")
            continue
        number = wave.get("wave")
        hunters = wave.get("hunters")
        if not isinstance(number, int) or isinstance(number, bool) or number < 1 or number in wave_map:
            errors.append(f"wave {index} must carry a unique positive wave number")
            continue
        if not isinstance(hunters, list) or not hunters or any(not agent(item) for item in hunters) or len(set(hunters)) != len(hunters):
            errors.append(f"wave {number} hunters must be unique agent ids")
            hunters = []
        if not agent(wave.get("critic")):
            errors.append(f"wave {number} critic must be an agent id")
        elif wave["critic"] in hunters:
            gates.append(f"wave {number} critic must not hunt in the same wave")
        else:
            critics.add(wave["critic"])
        listed = wave.get("units")
        if not isinstance(listed, list) or any(not isinstance(item, str) for item in listed) or len(set(listed)) != len(listed):
            errors.append(f"wave {number} units must be unique coverage ids")
            listed = []
        wave_map[number] = {"hunters": set(hunters), "units": set(listed)}

    units = data.get("units")
    if not isinstance(units, list):
        errors.append("units must be a list")
        units = []
    if len(units) > MAX_UNITS:
        errors.append(f"units exceed the limit of {MAX_UNITS}")
        units = []
    seen_ids: set[str] = set()
    seen_tuples: set[tuple[Any, ...]] = set()
    counts = {name: 0 for name in sorted(UNIT_STATUS)}
    for index, unit in enumerate(units):
        label = f"unit {index}"
        if not isinstance(unit, dict) or set(unit) != UNIT_KEYS:
            errors.append(f"{label} shape invalid")
            continue
        cid = unit.get("coverage_id")
        if isinstance(cid, str):
            label = f"unit {cid}"
        parts = tuple(unit.get(key) for key in ("surface", "boundary", "subsystem", "attack_class"))
        if any(not isinstance(part, str) for part in parts):
            errors.append(f"{label} dimension references must be strings")
            continue
        if parts[0] not in surfaces or parts[1] not in boundaries or parts[2] not in subsystems or parts[3] not in classes:
            errors.append(f"{label} references an unknown surface, boundary, subsystem, or attack class")
        if cid != coverage_id(*parts):
            errors.append(f"{label} coverage_id does not match its dimension tuple")
        if cid in seen_ids:
            errors.append(f"{label} coverage_id duplicated")
        if parts in seen_tuples:
            errors.append(f"{label} dimension tuple duplicated")
        if isinstance(cid, str):
            seen_ids.add(cid)
        seen_tuples.add(parts)
        status = unit.get("status")
        if status not in UNIT_STATUS:
            errors.append(f"{label} status invalid")
            continue
        counts[status] += 1
        owner, wave, reason = unit.get("owner"), unit.get("wave"), unit.get("unresolved_reason")
        if owner is not None and not agent(owner):
            errors.append(f"{label} owner must be an agent id or null")
            owner = None
        if wave is not None and (not isinstance(wave, int) or isinstance(wave, bool) or wave not in wave_map):
            errors.append(f"{label} wave must reference a declared wave or be null")
            wave = None
        if not optional_text(reason):
            errors.append(f"{label} unresolved_reason must be text or null")
        reviewed = unit.get("reviewed_paths")
        if not isinstance(reviewed, list) or any(not target_path_ok(item, target_root) for item in reviewed) or len(set(reviewed)) != len(reviewed):
            errors.append(f"{label} reviewed_paths must be unique, lexically safe, and present under the target root")
            reviewed = []
        checks = unit.get("checks")
        if not isinstance(checks, list):
            errors.append(f"{label} checks must be a list")
            checks = []
        check_ids: set[str] = set()
        for position, check in enumerate(checks):
            if not isinstance(check, dict) or set(check) != {"id", "method", "description", "paths", "result_fingerprint"} or not text(check.get("id")) or check.get("method") not in CHECK_METHODS or not text(check.get("description")) or not isinstance(check.get("paths"), list) or any(not target_path_ok(item, target_root) for item in check["paths"]) or not isinstance(check.get("result_fingerprint"), str) or not HEX16.fullmatch(check["result_fingerprint"]):
                errors.append(f"{label} check {position} invalid")
                continue
            if check["id"] in check_ids:
                errors.append(f"{label} check id duplicated: {check['id']}")
            check_ids.add(check["id"])
            if check["method"] == "local" and not sandbox_available:
                gates.append(f"{label} local check requires an available sandbox")
        fingerprints = unit.get("candidate_fingerprints")
        if not isinstance(fingerprints, list) or any(not isinstance(item, str) or not FINGERPRINT.fullmatch(item) for item in fingerprints) or len(set(fingerprints)) != len(fingerprints):
            errors.append(f"{label} candidate_fingerprints must be unique sa1- fingerprints")
            fingerprints = []
        proposed = unit.get("proposed_by")
        if proposed is not None:
            if not agent(proposed):
                errors.append(f"{label} proposed_by must be an agent id or null")
            elif proposed not in critics:
                gates.append(f"{label} proposed_by must be a wave critic")
            elif proposed == owner:
                gates.append(f"{label} proposed_by must differ from the owner")
        carried = unit.get("carried_from")
        source_changed = False
        if carried is not None:
            if not isinstance(carried, dict) or set(carried) != {"run_id", "prior_status", "source_changed"} or not isinstance(carried.get("run_id"), str) or carried.get("prior_status") not in UNIT_STATUS or not isinstance(carried.get("source_changed"), bool):
                errors.append(f"{label} carried_from must be {{run_id, prior_status, source_changed}} or null")
                carried = None
            elif carried["run_id"] not in prior_ids:
                gates.append(f"{label} carried from a run outside run.prior_runs")
            else:
                source_changed = carried["source_changed"]
        carried_unchanged = carried is not None and not source_changed
        hunted_this_run = status == "in_progress" or not carried_unchanged
        if status == "planned":
            if owner is not None or wave is not None or reviewed or checks or fingerprints or reason is not None:
                errors.append(f"{label} planned units carry no owner, wave, paths, checks, fingerprints, or reason")
            continue
        if status in {"in_progress", "covered", "candidate"} and hunted_this_run and (owner is None or wave is None):
            errors.append(f"{label} {status} requires an owner and a wave" + (" (source changed since the carried run)" if source_changed else ""))
        if status in {"covered", "candidate"}:
            if not reviewed or not checks:
                errors.append(f"{label} {status} requires reviewed_paths and checks" + (" fresh after a source change" if source_changed else ""))
            if reason is not None:
                errors.append(f"{label} {status} must carry a null unresolved_reason")
            if status == "covered" and fingerprints:
                errors.append(f"{label} covered units carry no candidate fingerprints")
            if status == "candidate" and not fingerprints:
                errors.append(f"{label} candidate requires at least one candidate fingerprint")
        if status in {"blocked", "deferred", "out_of_scope", "not_applicable"} and not text(reason):
            errors.append(f"{label} {status} requires an unresolved_reason")
        if status in {"out_of_scope", "not_applicable"} and checks:
            errors.append(f"{label} {status} carries no checks")
        if owner is not None and wave is not None and status in {"in_progress", "covered", "candidate"}:
            if owner not in wave_map[wave]["hunters"]:
                gates.append(f"{label} owner {owner} is not a hunter of wave {wave}")
            if isinstance(cid, str) and cid not in wave_map[wave]["units"]:
                gates.append(f"{label} is not listed in wave {wave}")

    for number, wave in sorted(wave_map.items()):
        unknown = sorted(wave["units"] - seen_ids)
        if unknown:
            errors.append(f"wave {number} lists unknown units: {unknown}")

    if run_status == "complete":
        if counts["planned"] or counts["in_progress"]:
            gates.append("complete run still has planned or in_progress units")
        expected_cells = {(s, b, u, c) for s in surfaces for b in boundaries for u in subsystems for c in classes}
        missing = expected_cells - seen_tuples
        if missing:
            gates.append(f"complete run is missing {len(missing)} coverage cell(s)")
    expected_total = len(surfaces) * len(boundaries) * len(subsystems) * len(classes)
    summary = obj(data.get("summary"))
    if set(summary) != {"expected_cells", "units", "by_status"} or summary.get("expected_cells") != expected_total or summary.get("units") != len(units) or summary.get("by_status") != counts:
        errors.append("summary counts do not match the ledger")
    return cap(errors), cap(gates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a security-audit coverage ledger.")
    parser.add_argument("ledger")
    parser.add_argument("--evidence-root", default=".")
    parser.add_argument("--target-root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    path = regular_input_file(args.ledger)
    if path is None:
        print("ledger must be a regular file, not a symlink", file=sys.stderr)
        return 2
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            print(f"ledger exceeds {MAX_FILE_BYTES} bytes", file=sys.stderr)
            return 2
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    target_root = Path(args.target_root) if args.target_root else None
    errors, gates = validate(data, Path(args.evidence_root), target_root)
    result = {"valid": not errors and not gates, "errors": errors, "gates": gates}
    print(json.dumps(result, indent=2) if args.json else ("Security coverage ledger valid" if result["valid"] else "\n".join([*(f"error: {item}" for item in errors), *(f"gate: {item}" for item in gates)])))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
