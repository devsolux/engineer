#!/usr/bin/env python3
"""Validate an Engineer capability ownership and skill-promotion decision."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import regular_input_file, safe_path

HEX = lambda value: isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
CHOICES = {"reuse", "extend-engineer", "extend-skill", "new-skill", "project-instruction", "project-code", "reject"}
EVAL_KINDS = {"positive", "negative", "ambiguous", "coexistence", "safety", "output-quality"}


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_binding(binding: Any, root: Path, label: str, errors: list[str], gates: list[str]) -> Any:
    if not isinstance(binding, dict) or set(binding) != {"path", "sha256"} or not text(binding.get("path")) or not HEX(binding.get("sha256")):
        errors.append(f"{label} binding invalid")
        return None
    path = safe_path(binding["path"], root)
    if path is None or not path.is_file():
        gates.append(f"{label} artifact unavailable or unsafe")
        return None
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
            gates.append(f"{label} artifact digest mismatch")
            return None
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        gates.append(f"{label} artifact invalid: {exc}")
        return None


def validate(data: Any, evidence_root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    root_keys = {"schema_version", "receipt_kind", "candidate", "signals", "catalog", "options", "decision", "authority", "evaluation", "lifecycle", "review", "evidence", "limitations"}
    if not isinstance(data, dict):
        return ["root must be an object"], []
    if set(data) != root_keys:
        errors.append(f"root keys must be exactly {sorted(root_keys)}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("receipt_kind") not in {"illustrative_fixture", "captured_assessment"}:
        errors.append("receipt_kind invalid")

    candidate = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
    candidate_keys = {"id", "job", "stable_inputs", "stable_outputs", "on_demand_depth", "specialized", "consequence", "expected_reuse", "proposed_owner", "owns", "excludes"}
    if set(candidate) != candidate_keys:
        errors.append("candidate shape invalid")
    if not all(text(candidate.get(key)) for key in ("id", "job", "proposed_owner")):
        errors.append("candidate identity, job, and owner required")
    if any(not isinstance(candidate.get(key), bool) for key in ("stable_inputs", "stable_outputs", "on_demand_depth", "specialized")):
        errors.append("candidate stability and specialization fields must be boolean")
    if candidate.get("consequence") not in {"low", "medium", "high", "safety-critical"}:
        errors.append("candidate consequence invalid")
    if not isinstance(candidate.get("expected_reuse"), int) or isinstance(candidate.get("expected_reuse"), bool) or not 0 <= candidate.get("expected_reuse", -1) <= 100000:
        errors.append("candidate expected_reuse invalid")
    for key in ("owns", "excludes"):
        values = candidate.get(key)
        if not isinstance(values, list) or not values or any(not text(value) for value in values) or len(set(values)) != len(values):
            errors.append(f"candidate {key} must be a non-empty unique text list")

    signals = data.get("signals") if isinstance(data.get("signals"), dict) else {}
    if set(signals) != {"occurrences", "ship_blocking", "safety_critical", "telemetry_cluster_sha256"}:
        errors.append("signals shape invalid")
    occurrences = signals.get("occurrences") if isinstance(signals.get("occurrences"), list) else []
    observed: set[tuple[str, str]] = set()
    evidence_ids: set[str] = set()
    for index, row in enumerate(occurrences):
        keys = {"evidence_id", "project_id", "task_id", "source_sha256"}
        if not isinstance(row, dict) or set(row) != keys or not all(text(row.get(key)) for key in ("evidence_id", "project_id", "task_id")) or not HEX(row.get("source_sha256")):
            errors.append(f"signal occurrence {index} invalid")
            continue
        if row["evidence_id"] in evidence_ids or (row["project_id"], row["task_id"]) in observed:
            errors.append("signal occurrences must have unique evidence and project/task identities")
        evidence_ids.add(row["evidence_id"]); observed.add((row["project_id"], row["task_id"]))
    if any(not isinstance(signals.get(key), bool) for key in ("ship_blocking", "safety_critical")):
        errors.append("signal consequence flags must be boolean")
    if signals.get("telemetry_cluster_sha256") is not None and not HEX(signals.get("telemetry_cluster_sha256")):
        errors.append("telemetry cluster digest invalid")
    signal_qualified = len(observed) >= 3 or signals.get("ship_blocking") is True or signals.get("safety_critical") is True

    catalog = data.get("catalog") if isinstance(data.get("catalog"), dict) else {}
    if set(catalog) != {"inventory_sha256", "skill_creator_loaded", "candidates"} or not HEX(catalog.get("inventory_sha256")) or not isinstance(catalog.get("skill_creator_loaded"), bool):
        errors.append("catalog binding invalid")
    catalog_rows = catalog.get("candidates") if isinstance(catalog.get("candidates"), list) else []
    catalog_names: set[str] = set()
    for index, row in enumerate(catalog_rows):
        keys = {"name", "owner_class", "current", "fit", "routing_overlap", "evidence"}
        if not isinstance(row, dict) or set(row) != keys or not all(text(row.get(key)) for key in ("name", "owner_class", "evidence")) or row.get("owner_class") not in {"engineer", "installed-skill", "project"} or not isinstance(row.get("current"), bool) or row.get("fit") not in {"worse", "equal", "better"} or row.get("routing_overlap") not in {"none", "bounded", "conflict"}:
            errors.append(f"catalog candidate {index} invalid")
            continue
        if row["name"] in catalog_names:
            errors.append("catalog candidate names must be unique")
        catalog_names.add(row["name"])
    if "engineer" not in catalog_names:
        gates.append("catalog comparison must include Engineer")

    options = data.get("options") if isinstance(data.get("options"), list) else []
    option_map: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(options):
        keys = {"choice", "fit", "maintenance_cost", "routing_risk", "evidence_strength", "reason"}
        if not isinstance(row, dict) or set(row) != keys or row.get("choice") not in CHOICES or row.get("fit") not in {"no", "partial", "yes"} or row.get("maintenance_cost") not in {"low", "medium", "high"} or row.get("routing_risk") not in {"low", "medium", "high"} or row.get("evidence_strength") not in {"weak", "moderate", "strong"} or not text(row.get("reason")):
            errors.append(f"ownership option {index} invalid")
            continue
        if row["choice"] in option_map:
            errors.append("ownership options must be unique")
        option_map[row["choice"]] = row
    if set(option_map) != CHOICES:
        gates.append("all ownership classes must be compared exactly once")

    decision = data.get("decision") if isinstance(data.get("decision"), dict) else {}
    decision_keys = {"choice", "phase", "target", "skill_mutation", "recursive_creation", "reason"}
    if set(decision) != decision_keys or decision.get("choice") not in CHOICES or decision.get("phase") not in {"assess", "draft", "apply", "install", "reject"} or not text(decision.get("target")) or not isinstance(decision.get("skill_mutation"), bool) or not isinstance(decision.get("recursive_creation"), bool) or not text(decision.get("reason")):
        errors.append("decision shape invalid")
    choice = decision.get("choice")
    mutation_choices = {"extend-engineer", "extend-skill", "new-skill"}
    if decision.get("skill_mutation") != (choice in mutation_choices):
        gates.append("skill_mutation must derive from the ownership choice")
    if decision.get("recursive_creation") is not False:
        gates.append("recursive skill creation is forbidden")
    selected = option_map.get(choice, {})
    if selected.get("fit") != "yes" or selected.get("routing_risk") == "high" or selected.get("evidence_strength") == "weak":
        gates.append("selected ownership option lacks sufficient fit, routing safety, or evidence")

    authority = data.get("authority") if isinstance(data.get("authority"), dict) else {}
    if set(authority) != {"allowed_destinations", "global_install", "external_repository_mutation"} or not isinstance(authority.get("allowed_destinations"), list) or any(not text(value) for value in authority.get("allowed_destinations", [])) or len(set(authority.get("allowed_destinations", []))) != len(authority.get("allowed_destinations", [])) or any(not isinstance(authority.get(key), bool) for key in ("global_install", "external_repository_mutation")):
        errors.append("authority shape invalid")
    if decision.get("phase") in {"apply", "install"} and decision.get("target") not in authority.get("allowed_destinations", []):
        gates.append("decision target is outside granted destinations")
    if decision.get("phase") == "install" and authority.get("global_install") is not True:
        gates.append("global installation is not authorized")

    evaluation = data.get("evaluation") if isinstance(data.get("evaluation"), dict) else {}
    if set(evaluation) != {"frozen_before_edit", "cases", "hosts", "models"} or not isinstance(evaluation.get("frozen_before_edit"), bool):
        errors.append("evaluation shape invalid")
    cases = evaluation.get("cases") if isinstance(evaluation.get("cases"), list) else []
    case_kinds: set[str] = set()
    for index, row in enumerate(cases):
        if not isinstance(row, dict) or set(row) != {"id", "kind"} or not text(row.get("id")) or row.get("kind") not in EVAL_KINDS or row.get("kind") in case_kinds:
            errors.append(f"evaluation case {index} invalid or duplicate")
            continue
        case_kinds.add(row["kind"])
    if any(not isinstance(evaluation.get(key), list) or not evaluation.get(key) or any(not text(value) for value in evaluation.get(key, [])) for key in ("hosts", "models")):
        errors.append("evaluation hosts and models must be non-empty text lists")
    if choice in mutation_choices and (evaluation.get("frozen_before_edit") is not True or case_kinds != EVAL_KINDS):
        gates.append("skill mutation requires frozen positive, negative, ambiguous, coexistence, safety, and output-quality cases")

    lifecycle = data.get("lifecycle") if isinstance(data.get("lifecycle"), dict) else {}
    if set(lifecycle) != {"owner", "review_cadence_days", "rollback", "deprecation"} or not all(text(lifecycle.get(key)) for key in ("owner", "rollback", "deprecation")) or not isinstance(lifecycle.get("review_cadence_days"), int) or isinstance(lifecycle.get("review_cadence_days"), bool) or not 1 <= lifecycle.get("review_cadence_days", 0) <= 730:
        errors.append("lifecycle contract invalid")

    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    if set(review) != {"maker", "checker", "approved"} or not all(text(review.get(key)) for key in ("maker", "checker")) or review.get("maker") == review.get("checker") or not isinstance(review.get("approved"), bool):
        errors.append("independent review invalid")
    if decision.get("phase") in {"apply", "install"} and review.get("approved") is not True:
        gates.append("apply or install requires independent approval")
    if choice in mutation_choices and (not signal_qualified or not all(candidate.get(key) is True for key in ("stable_inputs", "stable_outputs", "on_demand_depth", "specialized")) or candidate.get("expected_reuse", 0) < 3 and candidate.get("consequence") not in {"high", "safety-critical"}):
        gates.append("skill mutation lacks a qualified signal and stable specialized on-demand contract")
    if choice in mutation_choices and catalog.get("skill_creator_loaded") is not True:
        gates.append("skill mutation requires the current skill-creator contract")
    if choice == "new-skill" and any(row.get("fit") in {"equal", "better"} and row.get("routing_overlap") != "conflict" for row in catalog_rows):
        gates.append("new skill duplicates an equal or better current owner")

    evidence = data.get("evidence")
    if data.get("receipt_kind") == "illustrative_fixture":
        if evidence is not None:
            gates.append("illustrative receipt evidence must be null")
    elif data.get("receipt_kind") == "captured_assessment":
        required = {"signals", "catalog", "authority", "review"}
        if not isinstance(evidence, dict) or set(evidence) != required:
            errors.append("captured assessment requires exact signal, catalog, authority, and review bindings")
        else:
            captured_signals = load_binding(evidence.get("signals"), evidence_root, "signals", errors, gates)
            captured_catalog = load_binding(evidence.get("catalog"), evidence_root, "catalog", errors, gates)
            captured_authority = load_binding(evidence.get("authority"), evidence_root, "authority", errors, gates)
            captured_review = load_binding(evidence.get("review"), evidence_root, "review", errors, gates)
            if captured_signals != {"candidate_id": candidate.get("id"), **signals}:
                gates.append("captured signal artifact differs from the receipt")
            expected_catalog = {"candidate_id": candidate.get("id"), "skill_creator_loaded": catalog.get("skill_creator_loaded"), "candidates": catalog_rows}
            if captured_catalog != expected_catalog:
                gates.append("captured catalog artifact differs from the receipt")
            elif evidence.get("catalog", {}).get("sha256") != catalog.get("inventory_sha256"):
                gates.append("catalog inventory digest differs from its evidence binding")
            if captured_authority != {"candidate_id": candidate.get("id"), **authority}:
                gates.append("captured authority artifact differs from the receipt")
            expected_review = {"candidate_id": candidate.get("id"), "decision_sha256": canonical_sha(decision), **review}
            if captured_review != expected_review:
                gates.append("captured review artifact differs from the receipt decision")

    limitations = data.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(not text(value) for value in limitations):
        errors.append("limitations must be a non-empty text list")
    return errors, gates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("receipt")
    parser.add_argument("--evidence-root", default=".")
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
    errors, gates = validate(data, Path(args.evidence_root))
    result = {"valid": not errors and not gates, "errors": errors, "gates": gates}
    print(json.dumps(result, indent=2) if args.json else ("Capability promotion valid" if result["valid"] else "\n".join([*(f"error: {item}" for item in errors), *(f"gate: {item}" for item in gates)])))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
