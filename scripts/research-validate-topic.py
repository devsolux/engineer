#!/usr/bin/env python3
"""Validate a complete deep-research topic before comparison or publication."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from research_contract import ResearchContractError, load_yaml_or_json, resolve_regular_file, resolve_results_dir


def normalized_name(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def find_item_name(data: object) -> object:
    if isinstance(data, dict):
        if isinstance(data.get("name"), (str, int, float)):
            return data["name"]
        for key, value in data.items():
            if key not in {"evidence", "uncertain", "sources"}:
                found = find_item_name(value)
                if found is not None:
                    return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deep-research topic coverage and evidence consistency")
    parser.add_argument("--topic-dir", "-t", required=True)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()

    root = Path(args.topic_dir).resolve()
    outline_path = root / "outline.yaml"
    fields_path = root / "fields.yaml"
    errors = []
    if not outline_path.is_file() or outline_path.is_symlink():
        errors.append("outline.yaml must be a regular file")
    if not fields_path.is_file() or fields_path.is_symlink():
        errors.append("fields.yaml must be a regular file")
    if errors:
        print("\n".join(f"[ERROR] {error}" for error in errors), file=sys.stderr)
        return 1

    try:
        outline = load_yaml_or_json(outline_path)
        fields = load_yaml_or_json(fields_path)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    try:
        output_dir = resolve_results_dir(root, outline)
    except ResearchContractError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    outline_items = outline.get("items")
    if not isinstance(outline_items, list) or not outline_items:
        errors.append("outline.items must be a non-empty array")
        outline_names = []
    else:
        outline_names = [normalized_name(item.get("name") if isinstance(item, dict) else None) for item in outline_items]
        if any(not name for name in outline_names):
            errors.append("every outline item must have a non-empty name")
        if len(outline_names) != len(set(outline_names)):
            errors.append("outline item names must be unique after normalization")

    result_paths = sorted(output_dir.glob("*.json"))
    if not result_paths:
        errors.append("results directory contains no JSON items")
    safe_result_paths = []
    result_names = []
    source_identity = {}
    expected_as_of = outline.get("as_of")
    evidence_policy = fields.get("evidence_policy") if isinstance(fields.get("evidence_policy"), dict) else {}
    evidence_required = evidence_policy.get("mode") == "claim_v1"
    semantic_review_required = evidence_policy.get("semantic_review") == "required"
    for path in result_paths:
        try:
            safe_path = resolve_regular_file(output_dir, path.name, label=f"result {path.name}")
        except ResearchContractError:
            errors.append(f"unsafe result path: {path.name}")
            continue
        safe_result_paths.append(safe_path)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid result JSON {path.name}: {exc}")
            continue
        name = normalized_name(find_item_name(data))
        if not name:
            errors.append(f"result {path.name} has no item name")
        result_names.append(name)
        evidence = data.get("evidence") if isinstance(data, dict) else None
        if evidence_required:
            if not expected_as_of:
                errors.append("outline.as_of is required by claim_v1")
            elif not isinstance(evidence, dict) or evidence.get("as_of") != expected_as_of:
                errors.append(f"result {path.name} evidence.as_of must equal outline.as_of")
        if isinstance(evidence, dict):
            for source in evidence.get("sources") or []:
                if not isinstance(source, dict) or not isinstance(source.get("url"), str):
                    continue
                identity = tuple(source.get(key) for key in ("publisher", "source_type", "published_at", "immutable_ref"))
                previous = source_identity.setdefault(source["url"], identity)
                if previous != identity:
                    errors.append(f"source metadata conflicts across items: {source['url']}")

    if len(result_names) != len(set(result_names)):
        errors.append("result item names must be unique after normalization")
    missing = sorted(set(outline_names) - set(result_names))
    extra = sorted(set(result_names) - set(outline_names))
    if missing:
        errors.append("missing outlined results: " + ", ".join(missing))
    if extra:
        errors.append("unapproved result items: " + ", ".join(extra))

    validator = Path(__file__).with_name("research-validate-json.py")
    if safe_result_paths:
        item_validation = subprocess.run(
            [sys.executable, str(validator), "--quiet", "--fields", str(fields_path), "--json", *map(str, safe_result_paths)],
            capture_output=True,
            text=True,
            check=False,
        )
        if item_validation.returncode:
            errors.append("one or more item evidence contracts failed")

    if semantic_review_required:
        review_path = root / "review.json"
        review_validator = Path(__file__).with_name("research-validate-review.py")
        review_validation = subprocess.run(
            [sys.executable, str(review_validator), "--quiet", "--topic-dir", str(root), str(review_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if review_validation.returncode:
            errors.append("required semantic claim review failed")
        else:
            try:
                review_decision = json.loads(review_path.read_text(encoding="utf-8")).get("decision")
            except (OSError, json.JSONDecodeError):
                review_decision = None
            if review_decision != "pass":
                errors.append("required semantic claim review did not pass")

    if errors:
        print("\n".join(f"[ERROR] {error}" for error in errors), file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"research topic valid ({len(result_paths)} item(s), as_of={expected_as_of or 'unbound'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
