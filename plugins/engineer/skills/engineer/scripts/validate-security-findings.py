#!/usr/bin/env python3
"""Validate an Engineer security-audit findings document (findings.json).

A finding is one of exactly three verdicts: ``confirmed`` (complete entrypoint
to sink trace, bound evidence, conditions, remediation, severity, independent
record review), ``needs_validation`` (named blockers and a validation plan, no
severity) or ``rejected`` (a refutation by the verifier). The record fingerprint
is recomputed here and never trusted from the document:

    fingerprint = "sa1-" + sha256("attack_class|root_cause.path|symbol|sink")[:16]

with ``symbol`` and ``sink`` serialized as empty strings when null, so the
identity stays stable across runs, line moves, agents, and severity changes.

Bindings: ``run.coverage`` and ``run.architecture`` are ``{path, sha256}``
relative to ``--evidence-root``; the bound ledger must pass
``validate-security-coverage.py`` (run in a subprocess with the same
interpreter) and carry the same ``run_id``. ``run.artifact_root`` is a directory
under ``--evidence-root``; every evidence file and report path is confined
beneath it. Target paths are lexically confined and, when ``--target-root`` is
given, must exist under it. The serialized document, every evidence file and
every report are screened for credential-shaped material; URLs may only point
at loopback or ``example.`` hosts.

Profiles (quick, standard, deep) change hunting breadth only; they never relax
a rule in this validator. ``--json`` prints ``{"valid", "errors", "gates"}``.
Exit 0 valid, 1 invalid, 2 unreadable input. Errors are shape or derivation
faults; gates are policy or consistency faults. Both block. Each list is capped
at 100 entries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

ATTACK_CLASSES = {"injection", "access_control", "resource_handling", "crypto_secrets", "business_logic", "feature_abuse", "chained_trust", "wildcard"}
DOMAINS = {"web_auth", "client_side", "ai_agent", "supply_chain", "cloud_infra", "protocols_messaging", "availability", "data_isolation"}
PROFILES = {"quick", "standard", "deep"}
RECEIPT_KINDS = {"illustrative_fixture", "captured_run"}
VERDICTS = {"confirmed", "needs_validation", "rejected"}
STAGE_RANK = {"entrypoint": 0, "propagation": 1, "sink": 2}
EVIDENCE_KINDS = {"source_excerpt", "local_execution", "test", "config", "git_history", "log"}
CONDITION_KINDS = {"authentication_level", "authorization_role", "user_interaction", "system_configuration", "network_routing", "environmental_dependency", "data_state", "timing_dependency", "third_party_dependency"}
BLOCKER_KINDS = {"deployment", "runtime", "configuration", "data"}
LEVELS = {"low": 0, "medium": 1, "high": 2, "critical": 3}
LIKELIHOODS = {"low", "medium", "high"}
CONFIDENCES = {"low", "medium", "high"}
AGENT_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
RUN_ID = re.compile(r"^run-[0-9]{3,}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
RECORD_KEYS = {"fingerprint", "title", "verdict", "attack_class", "domain", "root_cause", "coverage_ids", "boundary", "trace", "evidence", "conditions", "confidence", "verification", "carried_from"}
VERDICT_KEYS = {
    "confirmed": {"severity", "remediation"},
    "needs_validation": {"blockers", "validation_plan"},
    "rejected": {"rejection"},
}
OPTIONAL_KEYS = set().union(*VERDICT_KEYS.values())
SPENT_KEYS = {"reconnaissance", "hunting", "critics", "verification", "record_review", "reporting"}
FORBIDDEN_CONTENT = re.compile(
    r"BEGIN (RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"
    r"|\bAKIA[0-9A-Z]{12,}|\bASIA[0-9A-Z]{12,}"
    r"|\bsk-[A-Za-z0-9_-]{12,}|\bsk_(live|test)_[A-Za-z0-9]{8,}"
    r"|\bghp_[A-Za-z0-9]{20,}|\bgithub_pat_[A-Za-z0-9_]{20,}"
    r"|\bxox[baprs]-[A-Za-z0-9-]{10,}|\bAIza[0-9A-Za-z_-]{30,}"
    r"|\bBearer\s+(?=[A-Za-z._~+/=-]*[0-9])[A-Za-z0-9._~+/=-]{16,}"
    r"|\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
    re.IGNORECASE,
)
URL = re.compile(r"\b[a-z][a-z0-9+.-]*://([^/\s\"'<>\\]+)", re.IGNORECASE)
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_EVIDENCE_BYTES = 1024 * 1024
MAX_TOTAL_EVIDENCE_BYTES = 32 * 1024 * 1024
MAX_RECORDS = 2000
MAX_ITEMS = 100
COVERAGE_VALIDATOR = Path(__file__).resolve().with_name("validate-security-coverage.py")


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def optional_text(value: Any) -> bool:
    return value is None or text(value)


def obj(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def agent(value: Any) -> bool:
    return isinstance(value, str) and AGENT_ID.fullmatch(value) is not None


def number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def fingerprint(attack_class: str, path: str, symbol: str | None, sink: str | None) -> str:
    return "sa1-" + hashlib.sha256(f"{attack_class}|{path}|{symbol or ''}|{sink or ''}".encode()).hexdigest()[:16]


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


def host_allowed(authority: str) -> bool:
    host = authority.rsplit("@", 1)[-1]
    host = host[1:host.index("]")] if host.startswith("[") and "]" in host else host.split(":", 1)[0]
    host = host.lower().rstrip(".")
    if host in {"localhost", "::1", "0.0.0.0"} or host.startswith("127."):
        return True
    if host.endswith((".localhost", ".example", ".test", ".invalid")):
        return True
    return re.fullmatch(r"([a-z0-9-]+\.)*example(\.[a-z0-9-]+)+", host) is not None


def screen(label: str, body: str, errors: list[str]) -> None:
    if FORBIDDEN_CONTENT.search(body):
        errors.append(f"{label} contains credential-shaped material")
    hosts = sorted({match.group(1) for match in URL.finditer(body) if not host_allowed(match.group(1))})
    if hosts:
        errors.append(f"{label} references non-fixture hosts: {hosts[:5]}")


def cap(items: list[str]) -> list[str]:
    if len(items) <= MAX_ITEMS:
        return items
    return items[: MAX_ITEMS - 1] + [f"{len(items) - MAX_ITEMS + 1} further item(s) suppressed"]


def load_binding(binding: Any, root: Path, label: str, errors: list[str], gates: list[str]) -> tuple[bytes | None, Path | None]:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"} or not text(binding.get("path")) or not isinstance(binding.get("sha256"), str) or not HEX64.fullmatch(binding["sha256"]):
        errors.append(f"{label} binding must be {{path, sha256}}")
        return None, None
    path = safe_path(binding["path"], root)
    if path is None or not path.is_file():
        gates.append(f"{label} artifact unavailable or unsafe")
        return None, None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        gates.append(f"{label} artifact unreadable: {exc}")
        return None, None
    if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
        gates.append(f"{label} artifact digest mismatch")
        return None, path
    return raw, path


def coverage_report(path: Path, evidence_root: Path, target_root: Path | None) -> tuple[bool, list[str]]:
    command = [sys.executable, str(COVERAGE_VALIDATOR), str(path), "--evidence-root", str(evidence_root), "--json"]
    if target_root is not None:
        command += ["--target-root", str(target_root)]
    try:
        run = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, [f"coverage validator did not complete: {exc}"]
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError:
        return False, [run.stderr.strip() or "coverage validator produced no report"]
    details = [*report.get("errors", []), *report.get("gates", [])]
    return run.returncode == 0 and report.get("valid") is True, details[:5]


def check_trace(trace: Any, label: str, verdict: str, target_root: Path | None, errors: list[str]) -> None:
    if not isinstance(trace, list):
        errors.append(f"{label} trace must be a list")
        return
    stages: list[str] = []
    for index, step in enumerate(trace):
        line = step.get("line") if isinstance(step, dict) else None
        if not isinstance(step, dict) or set(step) != {"stage", "path", "symbol", "line", "note"} or step.get("stage") not in STAGE_RANK or not target_path_ok(step.get("path"), target_root) or not optional_text(step.get("symbol")) or not (line is None or (isinstance(line, int) and not isinstance(line, bool) and line >= 1)) or not text(step.get("note")):
            errors.append(f"{label} trace step {index} invalid")
            continue
        stages.append(step["stage"])
    if verdict == "rejected":
        return
    if not stages:
        errors.append(f"{label} requires at least one trace stage")
        return
    if stages[0] != "entrypoint":
        errors.append(f"{label} trace must start at an entrypoint")
    ranks = [STAGE_RANK[stage] for stage in stages]
    if ranks != sorted(ranks):
        errors.append(f"{label} trace stages must run entrypoint, propagation, sink in order")
    if verdict == "confirmed" and (len(stages) < 2 or stages[-1] != "sink"):
        errors.append(f"{label} confirmed trace needs at least two stages and must end at a sink")


def check_evidence(items: Any, label: str, verdict: str, artifact_root: Path | None, sandbox_available: bool, totals: list[int], errors: list[str], gates: list[str]) -> None:
    if not isinstance(items, list):
        errors.append(f"{label} evidence must be a list")
        return
    if verdict != "rejected" and not items:
        errors.append(f"{label} requires at least one evidence item")
    for index, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"kind", "path", "sha256", "bytes", "summary"} or item.get("kind") not in EVIDENCE_KINDS or not lexical_path(item.get("path")) or not isinstance(item.get("sha256"), str) or not HEX64.fullmatch(item["sha256"]) or not isinstance(item.get("bytes"), int) or isinstance(item.get("bytes"), bool) or item["bytes"] < 0 or not text(item.get("summary")):
            errors.append(f"{label} evidence {index} invalid")
            continue
        if item["kind"] == "local_execution" and not sandbox_available:
            gates.append(f"{label} local_execution evidence requires an available sandbox")
        if artifact_root is None:
            continue
        path = safe_path(item["path"], artifact_root)
        if path is None:
            gates.append(f"{label} evidence {index} path escapes the artifact root or crosses a symlink")
            continue
        if not path.is_file():
            gates.append(f"{label} evidence {index} unavailable")
            continue
        size = path.stat().st_size
        if size > MAX_EVIDENCE_BYTES:
            gates.append(f"{label} evidence {index} exceeds {MAX_EVIDENCE_BYTES} bytes")
            continue
        totals[0] += size
        if item["bytes"] != size:
            gates.append(f"{label} evidence {index} byte count mismatch")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item["sha256"]:
            gates.append(f"{label} evidence {index} digest mismatch")
        screen(f"{label} evidence {index}", raw.decode("utf-8", errors="replace"), errors)


def check_plan(plan: Any, label: str, errors: list[str]) -> None:
    if not isinstance(plan, dict) or set(plan) != {"local", "owner_observed"} or any(not isinstance(plan.get(key), list) for key in ("local", "owner_observed")):
        errors.append(f"{label} validation_plan must carry local and owner_observed lists")
        return
    if not plan["local"] and not plan["owner_observed"]:
        errors.append(f"{label} validation_plan needs at least one local or owner-observed step")
    for key in ("local", "owner_observed"):
        for index, step in enumerate(plan[key]):
            if not isinstance(step, dict) or set(step) != {"action", "expected_if_vulnerable", "expected_if_safe", "sandbox_required"} or not all(text(step.get(field)) for field in ("action", "expected_if_vulnerable", "expected_if_safe")) or not isinstance(step.get("sandbox_required"), bool):
                errors.append(f"{label} validation_plan {key} step {index} invalid")


def validate_run(run: dict[str, Any], kind: Any, errors: list[str], gates: list[str]) -> dict[str, Any]:
    keys = {"run_id", "target", "mode", "profile", "status", "incomplete_reason", "started_at", "ended_at", "prior_runs", "artifact_root", "coverage", "architecture", "reports", "sandbox", "safety", "budget"}
    if set(run) != keys:
        errors.append("run shape invalid")
    run_id = run.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        errors.append("run.run_id must match ^run-[0-9]{3,}$")
    target = obj(run.get("target"))
    if set(target) != {"name", "source_ref", "root"} or not all(text(target.get(key)) for key in ("name", "source_ref", "root")):
        errors.append("run.target must carry name, source_ref, and root")
    elif kind == "captured_run" and not HEX40.fullmatch(target["source_ref"]):
        errors.append("captured run requires a 40-hex source_ref")
    if run.get("mode") != "full_audit":
        errors.append("run.mode must be full_audit")
    if run.get("profile") not in PROFILES:
        errors.append("run.profile must be quick, standard, or deep")
    status = run.get("status")
    if status not in {"complete", "incomplete"}:
        errors.append("run.status must be complete or incomplete")
    reason = run.get("incomplete_reason")
    if status == "incomplete" and not text(reason):
        errors.append("incomplete run requires a non-empty incomplete_reason")
    if status == "complete" and reason is not None:
        errors.append("complete run must carry a null incomplete_reason")
    started, ended = timestamp(run.get("started_at")), timestamp(run.get("ended_at"))
    if started is None or ended is None:
        errors.append("run.started_at and run.ended_at must be ISO 8601 timestamps with timezone")
    elif ended < started:
        errors.append("run.ended_at must not precede run.started_at")
    prior = run.get("prior_runs")
    prior_ids: set[str] = set()
    if not isinstance(prior, list) or any(not isinstance(item, str) or not RUN_ID.fullmatch(item) for item in prior) or len(set(prior)) != len(prior) or run_id in prior:
        errors.append("run.prior_runs must be unique run ids excluding this run")
    else:
        prior_ids = set(prior)
    reports = run.get("reports")
    if not isinstance(reports, list) or any(not lexical_path(item) for item in reports) or len(set(reports)) != len(reports):
        errors.append("run.reports must be unique lexically safe paths")
        reports = []
    if kind == "captured_run" and status == "complete" and "REPORT.md" not in reports:
        gates.append("a complete captured run must list REPORT.md among its reports")
    sandbox = obj(run.get("sandbox"))
    limits = obj(sandbox.get("limits"))
    if set(sandbox) != {"available", "network", "env", "target_mount", "writes", "limits", "unavailable_reason"} or not isinstance(sandbox.get("available"), bool) or sandbox.get("network") != "none" or sandbox.get("env") != "empty_allowlist" or sandbox.get("target_mount") != "read_only" or sandbox.get("writes") != "scratch_only" or set(limits) != {"cpu_seconds", "memory_mb", "wall_seconds"} or any(not isinstance(limits.get(key), int) or isinstance(limits.get(key), bool) or limits[key] <= 0 for key in ("cpu_seconds", "memory_mb", "wall_seconds")):
        errors.append("run.sandbox must declare no network, an empty env allowlist, a read-only target mount, scratch-only writes, and positive limits")
    elif sandbox["available"] and sandbox.get("unavailable_reason") is not None:
        errors.append("available sandbox must carry a null unavailable_reason")
    elif not sandbox["available"] and not text(sandbox.get("unavailable_reason")):
        errors.append("unavailable sandbox requires a reason")
    safety = obj(run.get("safety"))
    if safety != {"source_inspection": "read_only", "live_systems_probed": False, "principals": "synthetic", "secrets": "synthetic"}:
        errors.append("run.safety must declare read-only inspection, no live probing, synthetic principals, and synthetic secrets")
    budget = obj(run.get("budget"))
    reserved = obj(budget.get("reserved"))
    spent = obj(budget.get("spent"))
    if set(budget) != {"unit", "total", "reserved", "reserved_before_hunting", "spent"} or not text(budget.get("unit")) or not number(budget.get("total")) or set(reserved) != {"critics", "verification"} or any(not number(reserved.get(key)) or reserved[key] <= 0 for key in ("critics", "verification")) or not isinstance(budget.get("reserved_before_hunting"), bool) or set(spent) != SPENT_KEYS or any(not number(spent.get(key)) for key in SPENT_KEYS):
        errors.append("run.budget must carry unit, total, positive critics and verification reserves, reserved_before_hunting, and all spent phases")
    else:
        if budget["reserved_before_hunting"] is not True:
            gates.append("critic and verification budget must be reserved before hunting")
        if sum(spent.values()) > budget["total"]:
            gates.append("budget spent exceeds the total")
        if spent["hunting"] > budget["total"] - reserved["critics"] - reserved["verification"]:
            gates.append("hunting consumed the reserve kept for critics and verification")
    return {"run_id": run_id, "started": started, "ended": ended, "prior_ids": prior_ids, "reports": reports, "sandbox_available": sandbox.get("available") is True, "status": status}


def validate(data: Any, evidence_root: Path, target_root: Path | None = None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    if not isinstance(data, dict):
        return ["root must be an object"], []
    root_keys = {"schema_version", "receipt_kind", "run", "records", "hardening_notes", "summary"}
    if set(data) != root_keys:
        errors.append(f"root keys must be exactly {sorted(root_keys)}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    kind = data.get("receipt_kind")
    if kind not in RECEIPT_KINDS:
        errors.append("receipt_kind invalid")
    screen("document", json.dumps(data, ensure_ascii=False), errors)

    run = obj(data.get("run"))
    facts = validate_run(run, kind, errors, gates)
    started, ended = facts["started"], facts["ended"]

    artifact_root: Path | None = None
    if not text(run.get("artifact_root")):
        errors.append("run.artifact_root must be a path under the evidence root")
    else:
        artifact_root = safe_path(run["artifact_root"], evidence_root)
        if artifact_root is None or not artifact_root.is_dir():
            gates.append("artifact root unavailable or unsafe")
            artifact_root = None
    coverage_raw, coverage_path = load_binding(run.get("coverage"), evidence_root, "coverage ledger", errors, gates)
    architecture_raw, _ = load_binding(run.get("architecture"), evidence_root, "architecture", errors, gates)
    unit_status: dict[str, str] | None = None
    if coverage_raw is not None and coverage_path is not None:
        ok, details = coverage_report(coverage_path, evidence_root, target_root)
        if not ok:
            gates.append(f"bound coverage ledger fails canonical validation: {details}")
        else:
            coverage = json.loads(coverage_raw)
            coverage_run = obj(coverage.get("run"))
            if coverage_run.get("run_id") != facts["run_id"]:
                gates.append("bound coverage ledger carries a different run_id")
            if coverage.get("receipt_kind") != kind:
                gates.append("bound coverage ledger carries a different receipt_kind")
            if architecture_raw is not None and obj(coverage_run.get("architecture")).get("sha256") != obj(run.get("architecture")).get("sha256"):
                gates.append("bound coverage ledger binds a different architecture brief")
            unit_status = {unit["coverage_id"]: unit["status"] for unit in coverage.get("units", [])}
    if artifact_root is not None:
        for report in facts["reports"]:
            path = safe_path(report, artifact_root)
            if path is None or not path.is_file():
                gates.append(f"report {report} unavailable or unsafe")
                continue
            screen(f"report {report}", path.read_bytes().decode("utf-8", errors="replace"), errors)

    records = data.get("records")
    if not isinstance(records, list):
        errors.append("records must be a list")
        records = []
    if len(records) > MAX_RECORDS:
        errors.append(f"records exceed the limit of {MAX_RECORDS}")
        records = []
    fingerprints: list[str] = []
    counts = {verdict: 0 for verdict in sorted(VERDICTS)}
    referenced: set[str] = set()
    totals = [0]
    for index, record in enumerate(records):
        label = f"record {index}"
        if not isinstance(record, dict) or not RECORD_KEYS <= set(record) or not set(record) <= RECORD_KEYS | OPTIONAL_KEYS:
            errors.append(f"{label} shape invalid")
            continue
        verdict = record.get("verdict")
        if verdict not in VERDICTS:
            errors.append(f"{label} verdict must be confirmed, needs_validation, or rejected")
            continue
        counts[verdict] += 1
        present = set(record) & OPTIONAL_KEYS
        if present != VERDICT_KEYS[verdict]:
            errors.append(f"{label} {verdict} must carry exactly {sorted(VERDICT_KEYS[verdict])} among the verdict-specific fields, found {sorted(present)}")
        if not text(record.get("title")):
            errors.append(f"{label} title required")
        attack_class = record.get("attack_class")
        if attack_class not in ATTACK_CLASSES:
            errors.append(f"{label} attack_class invalid")
        if record.get("domain") is not None and record.get("domain") not in DOMAINS:
            errors.append(f"{label} domain invalid")
        root_cause = obj(record.get("root_cause"))
        if set(root_cause) != {"path", "symbol", "sink", "note"} or not target_path_ok(root_cause.get("path"), target_root) or not optional_text(root_cause.get("symbol")) or not optional_text(root_cause.get("sink")) or not text(root_cause.get("note")):
            errors.append(f"{label} root_cause must carry path, symbol|null, sink|null, and note")
        elif attack_class in ATTACK_CLASSES:
            expected = fingerprint(attack_class, root_cause["path"], root_cause["symbol"], root_cause["sink"])
            if record.get("fingerprint") != expected:
                errors.append(f"{label} fingerprint does not match its root cause (expected {expected})")
        fp = record.get("fingerprint")
        if isinstance(fp, str):
            if fp in fingerprints:
                errors.append(f"{label} fingerprint duplicated: {fp}")
            fingerprints.append(fp)
            label = f"record {fp}"
        coverage_ids = record.get("coverage_ids")
        if not isinstance(coverage_ids, list) or not coverage_ids or any(not text(item) for item in coverage_ids) or len(set(coverage_ids)) != len(coverage_ids):
            errors.append(f"{label} coverage_ids must be a non-empty unique list")
            coverage_ids = []
        for cid in coverage_ids:
            if unit_status is None:
                continue
            if cid not in unit_status:
                errors.append(f"{label} references unknown coverage unit {cid}")
                continue
            referenced.add(cid)
            if verdict != "rejected" and unit_status[cid] != "candidate":
                gates.append(f"{label} references coverage unit {cid} with status {unit_status[cid]}, expected candidate")
        boundary = obj(record.get("boundary"))
        boundary_keys = ("principal", "input", "intended_control", "crossed", "result")
        if set(boundary) != set(boundary_keys) or any((not text(boundary.get(key))) if verdict != "rejected" else (not (boundary.get(key) is None or isinstance(boundary.get(key), str))) for key in boundary_keys):
            errors.append(f"{label} boundary must name principal, input, intended_control, crossed, and result")
        check_trace(record.get("trace"), label, verdict, target_root, errors)
        check_evidence(record.get("evidence"), label, verdict, artifact_root, facts["sandbox_available"], totals, errors, gates)
        conditions = record.get("conditions")
        if not isinstance(conditions, list) or any(not isinstance(item, dict) or set(item) != {"kind", "description"} or item.get("kind") not in CONDITION_KINDS or not text(item.get("description")) for item in conditions):
            errors.append(f"{label} conditions must be {{kind, description}} items")
            conditions = []
        if verdict == "confirmed" and not conditions:
            errors.append(f"{label} confirmed requires at least one condition")
        confidence = record.get("confidence")
        if confidence not in CONFIDENCES:
            errors.append(f"{label} confidence must be low, medium, or high")
        elif verdict == "confirmed" and confidence == "low":
            errors.append(f"{label} confirmed requires medium or high confidence")
        if "severity" in record:
            severity = obj(record.get("severity"))
            if set(severity) != {"likelihood", "impact", "overall"} or severity.get("likelihood") not in LIKELIHOODS or severity.get("impact") not in LEVELS or severity.get("overall") not in LEVELS:
                errors.append(f"{label} severity must carry likelihood, impact, and overall")
            elif LEVELS[severity["overall"]] > LEVELS[severity["impact"]]:
                gates.append(f"{label} overall severity exceeds the demonstrated impact")
        if "remediation" in record:
            remediation = obj(record.get("remediation"))
            if set(remediation) != {"summary", "layer", "paths", "regression_test"} or not text(remediation.get("summary")) or not text(remediation.get("layer")) or not isinstance(remediation.get("paths"), list) or any(not target_path_ok(item, target_root) for item in remediation["paths"]) or not optional_text(remediation.get("regression_test")):
                errors.append(f"{label} remediation must carry summary, layer, paths, and regression_test|null")
        if "blockers" in record:
            blockers = record.get("blockers")
            if not isinstance(blockers, list) or not blockers or any(not isinstance(item, dict) or set(item) != {"kind", "unresolved_fact", "why_it_matters"} or item.get("kind") not in BLOCKER_KINDS or not text(item.get("unresolved_fact")) or not text(item.get("why_it_matters")) for item in blockers):
                errors.append(f"{label} blockers must be a non-empty list of {{kind, unresolved_fact, why_it_matters}}")
        if "validation_plan" in record:
            check_plan(record.get("validation_plan"), label, errors)
        verification = obj(record.get("verification"))
        hunter, verifier = verification.get("hunter"), verification.get("verifier")
        if set(verification) != {"hunter", "verifier", "verifier_attempted_refutation", "verified_at", "record_reviewer", "materially_replaced", "replacement_verifier"} or not agent(hunter) or not agent(verifier) or verification.get("verifier_attempted_refutation") is not True or not isinstance(verification.get("materially_replaced"), bool) or not (verification.get("record_reviewer") is None or agent(verification.get("record_reviewer"))) or not (verification.get("replacement_verifier") is None or agent(verification.get("replacement_verifier"))):
            errors.append(f"{label} verification must carry hunter, verifier, an attempted refutation, verified_at, record_reviewer|null, materially_replaced, and replacement_verifier|null")
            verification = {}
        else:
            reviewer = verification["record_reviewer"]
            if hunter == verifier:
                gates.append(f"{label} verifier must not be the hunter")
            if verdict != "rejected" and reviewer is None:
                gates.append(f"{label} {verdict} requires an independent record reviewer")
            if reviewer is not None and reviewer in {hunter, verifier}:
                gates.append(f"{label} record reviewer must be independent of the hunter and verifier")
            replacement = verification["replacement_verifier"]
            if verification["materially_replaced"]:
                if replacement is None or replacement in {hunter, verifier, reviewer}:
                    gates.append(f"{label} material replacement requires an independent replacement verifier")
            elif replacement is not None:
                errors.append(f"{label} replacement_verifier must be null unless materially replaced")
            verified_at = timestamp(verification.get("verified_at"))
            if verified_at is None:
                errors.append(f"{label} verified_at must be an ISO 8601 timestamp with timezone")
            elif started is not None and ended is not None and not started <= verified_at <= ended:
                gates.append(f"{label} verified outside the run window")
        if "rejection" in record:
            rejection = obj(record.get("rejection"))
            if set(rejection) != {"reason", "refuted_by"} or not text(rejection.get("reason")) or not agent(rejection.get("refuted_by")):
                errors.append(f"{label} rejection must carry reason and refuted_by")
            elif verification and rejection["refuted_by"] != verification.get("verifier"):
                gates.append(f"{label} rejection must be refuted by the record verifier")
        carried = record.get("carried_from")
        if carried is not None:
            if not isinstance(carried, dict) or set(carried) != {"run_id", "prior_verdict", "reverified"} or not isinstance(carried.get("run_id"), str) or carried.get("prior_verdict") not in VERDICTS or not isinstance(carried.get("reverified"), bool):
                errors.append(f"{label} carried_from must be {{run_id, prior_verdict, reverified}} or null")
            else:
                if carried["run_id"] not in facts["prior_ids"]:
                    gates.append(f"{label} carried from a run outside run.prior_runs")
                if carried["reverified"] is not True:
                    gates.append(f"{label} carried finding was not re-verified in this run")
    if fingerprints != sorted(fingerprints):
        errors.append("records must be sorted by fingerprint")
    if totals[0] > MAX_TOTAL_EVIDENCE_BYTES:
        gates.append(f"evidence total exceeds {MAX_TOTAL_EVIDENCE_BYTES} bytes")

    notes = data.get("hardening_notes")
    if not isinstance(notes, list):
        errors.append("hardening_notes must be a list")
        notes = []
    note_ids: set[str] = set()
    for index, note in enumerate(notes):
        location = obj(note.get("location")) if isinstance(note, dict) else {}
        if not isinstance(note, dict) or set(note) != {"id", "title", "location", "note", "layer_preventing_attack", "coverage_ids"} or not text(note.get("id")) or not text(note.get("title")) or set(location) != {"path", "symbol"} or not target_path_ok(location.get("path"), target_root) or not optional_text(location.get("symbol")) or not text(note.get("note")) or not text(note.get("layer_preventing_attack")) or not isinstance(note.get("coverage_ids"), list) or any(not text(item) for item in note["coverage_ids"]) or len(set(note["coverage_ids"])) != len(note["coverage_ids"]):
            errors.append(f"hardening note {index} invalid")
            continue
        if note["id"] in note_ids:
            errors.append(f"hardening note id duplicated: {note['id']}")
        note_ids.add(note["id"])
        if unit_status is not None:
            for cid in note["coverage_ids"]:
                if cid not in unit_status:
                    errors.append(f"hardening note {note['id']} references unknown coverage unit {cid}")
    if unit_status is not None:
        for cid, status in sorted(unit_status.items()):
            if status == "candidate" and cid not in referenced:
                gates.append(f"candidate unit without a verdict: {cid}")

    summary = obj(data.get("summary"))
    expected = {**counts, "hardening_notes": len(notes), "clean": counts["confirmed"] == 0 and counts["needs_validation"] == 0}
    if summary != expected:
        errors.append("summary counts do not match the records and hardening notes")
    return cap(errors), cap(gates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a security-audit findings document.")
    parser.add_argument("findings")
    parser.add_argument("--evidence-root", default=".")
    parser.add_argument("--target-root", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    path = regular_input_file(args.findings)
    if path is None:
        print("findings must be a regular file, not a symlink", file=sys.stderr)
        return 2
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            print(f"findings exceed {MAX_FILE_BYTES} bytes", file=sys.stderr)
            return 2
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    target_root = Path(args.target_root) if args.target_root else None
    errors, gates = validate(data, Path(args.evidence_root), target_root)
    result = {"valid": not errors and not gates, "errors": errors, "gates": gates}
    print(json.dumps(result, indent=2) if args.json else ("Security findings valid" if result["valid"] else "\n".join([*(f"error: {item}" for item in errors), *(f"gate: {item}" for item in gates)])))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
