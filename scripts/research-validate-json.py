#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate deep-research JSON covers fields.yaml (required fields).

Vendored/adapted from Weizhena/Deep-Research-skills (MIT).
Copyright (c) 2026 Lan Zheng. See ../THIRD_PARTY_NOTICES.md for the license.
Requires PyYAML in the active environment.
"""

import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml  # supply-chain:allow — std research dependency
except ImportError:
    yaml = None

CATEGORY_MAPPING = {
    "basic_info": ["basic_info", "Basic Info"],
    "technical_features": ["technical_features", "technical_characteristics", "Technical Features"],
    "performance_metrics": ["performance_metrics", "performance", "Performance Metrics"],
    "milestone_significance": ["milestone_significance", "milestones", "Milestone Significance"],
    "business_info": ["business_info", "commercial_info", "Business Info"],
    "competition_ecosystem": ["competition_ecosystem", "competition", "Competition Ecosystem"],
    "history": ["history", "History"],
    "market_positioning": ["market_positioning", "market", "Market Positioning"],
}

_SKIP_KEYS = {"_source_file", "uncertain", "evidence"}
_ID = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
_SOURCE_TYPES = {"official_docs", "repository", "standard", "paper", "dataset", "regulator", "primary", "secondary"}
_CLAIM_KINDS = {"fact", "inference", "comparison"}
_CONFIDENCE = {"high", "medium", "low"}


def load_fields_yaml(fields_path):
    text = fields_path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "PyYAML is required for non-JSON YAML files. Install with: uv add pyyaml"
            ) from exc
    items = [
        (field["name"], category["category"], field.get("required", False))
        for category in data.get("field_categories", [])
        for field in category.get("fields", [])
    ]
    all_fields = {name for name, _, _ in items}
    required_fields = {name for name, _, required in items if required}
    field_categories = {name: category for name, category, _ in items}
    return all_fields, required_fields, field_categories, data.get("evidence_policy")


def _iso_date(value, label, errors):
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} must be an ISO date")
        return None


def validate_evidence(data, all_fields, required_fields, policy):
    if not policy:
        return []
    errors = []
    if not isinstance(policy, dict) or policy.get("mode") != "claim_v1":
        return ["evidence_policy must use mode claim_v1"]
    evidence = data.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != {"as_of", "sources", "claims"}:
        return ["evidence must contain exactly as_of, sources, and claims"]
    as_of = _iso_date(evidence.get("as_of"), "evidence.as_of", errors)
    if as_of and as_of > date.today():
        errors.append("evidence.as_of cannot be in the future")

    sources = evidence.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("evidence.sources must be a non-empty array")
        sources = []
    source_ids = set()
    for index, source in enumerate(sources):
        label = f"evidence.sources[{index}]"
        required = {"id", "title", "url", "publisher", "source_type", "accessed_at"}
        optional = {"published_at", "immutable_ref"}
        if not isinstance(source, dict) or not required <= set(source) or set(source) - required - optional:
            errors.append(f"{label} has missing or unknown keys")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not _ID.fullmatch(sid) or sid in source_ids:
            errors.append(f"{label}.id must be unique lowercase token")
        else:
            source_ids.add(sid)
        for key in ("title", "publisher"):
            if not isinstance(source.get(key), str) or not source[key].strip():
                errors.append(f"{label}.{key} must be non-empty")
        url = source.get("url")
        try:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.fragment:
                raise ValueError
        except (TypeError, ValueError):
            errors.append(f"{label}.url must be canonical HTTPS without credentials or fragment")
        if source.get("source_type") not in _SOURCE_TYPES:
            errors.append(f"{label}.source_type is not allowlisted")
        accessed = _iso_date(source.get("accessed_at"), f"{label}.accessed_at", errors)
        if accessed and as_of and accessed > as_of:
            errors.append(f"{label}.accessed_at cannot follow evidence.as_of")
        if "published_at" in source:
            published = _iso_date(source.get("published_at"), f"{label}.published_at", errors)
            if published and as_of and published > as_of:
                errors.append(f"{label}.published_at cannot follow evidence.as_of")
        if "immutable_ref" in source and (not isinstance(source["immutable_ref"], str) or not source["immutable_ref"].strip()):
            errors.append(f"{label}.immutable_ref must be non-empty when present")

    claims = evidence.get("claims")
    if not isinstance(claims, list) or not claims:
        errors.append("evidence.claims must be a non-empty array")
        claims = []
    claim_ids = set()
    covered_fields = set()
    for index, claim in enumerate(claims):
        label = f"evidence.claims[{index}]"
        keys = {"id", "field", "statement", "kind", "confidence", "source_ids"}
        if not isinstance(claim, dict) or set(claim) != keys:
            errors.append(f"{label} must contain exactly {', '.join(sorted(keys))}")
            continue
        cid = claim.get("id")
        if not isinstance(cid, str) or not _ID.fullmatch(cid) or cid in claim_ids:
            errors.append(f"{label}.id must be unique lowercase token")
        else:
            claim_ids.add(cid)
        field = claim.get("field")
        if field not in all_fields:
            errors.append(f"{label}.field is not defined in fields.yaml")
        else:
            covered_fields.add(field)
        if not isinstance(claim.get("statement"), str) or len(claim["statement"].strip()) < 8:
            errors.append(f"{label}.statement is too short")
        if claim.get("kind") not in _CLAIM_KINDS:
            errors.append(f"{label}.kind is not allowlisted")
        if claim.get("confidence") not in _CONFIDENCE:
            errors.append(f"{label}.confidence is not allowlisted")
        refs = claim.get("source_ids")
        if not isinstance(refs, list) or not refs or not all(isinstance(value, str) for value in refs):
            errors.append(f"{label}.source_ids must be a non-empty string array")
        else:
            unknown = set(refs) - source_ids
            if unknown:
                errors.append(f"{label}.source_ids reference unknown sources: {', '.join(sorted(unknown))}")
            if len(refs) != len(set(refs)):
                errors.append(f"{label}.source_ids must not contain duplicates")

    uncertain = set(data.get("uncertain") or [])
    identity = set(policy.get("identity_fields") or ["name"])
    if not identity <= all_fields:
        errors.append("evidence_policy.identity_fields contains undefined fields")
    required_claim_fields = required_fields - identity - uncertain
    missing_claims = required_claim_fields - covered_fields
    if missing_claims:
        errors.append("required fields lack claim evidence: " + ", ".join(sorted(missing_claims)))
    return errors


def extract_json_fields(data, category_mapping=None):
    category_mapping = CATEGORY_MAPPING if category_mapping is None else category_mapping
    nested_keys = {k for keys in category_mapping.values() for k in keys}
    fields = set()
    stack = [(data, True)]
    while stack:
        obj, is_category_level = stack.pop()
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in _SKIP_KEYS:
                    continue
                if is_category_level and k in nested_keys:
                    if isinstance(v, dict):
                        stack.append((v, True))
                    continue
                fields.add(k)
        elif isinstance(obj, list):
            stack.extend((item, is_category_level) for item in obj if isinstance(item, dict))
    return fields


def validate_json(json_path, all_fields, required_fields, field_categories, evidence_policy=None):
    with json_path.open(encoding="utf-8") as f:
        data = json.load(f)
    json_fields = extract_json_fields(data)
    uncertain_raw = data.get("uncertain", [])
    uncertainty_errors = []
    if not isinstance(uncertain_raw, list) or not all(isinstance(item, str) for item in uncertain_raw):
        uncertainty_errors.append("uncertain must be an array of field-name strings")
        uncertain_fields = set()
    else:
        uncertain_fields = set(uncertain_raw)
        unknown_uncertain = uncertain_fields - all_fields
        if unknown_uncertain:
            uncertainty_errors.append(
                "uncertain lists undefined fields: " + ", ".join(sorted(unknown_uncertain))
            )
    marker_fields = set()
    def find_markers(obj, field_name=None):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key not in _SKIP_KEYS:
                    find_markers(value, key)
        elif isinstance(obj, list):
            for value in obj:
                find_markers(value, field_name)
        elif isinstance(obj, str) and "[uncertain]" in obj.lower() and field_name:
            marker_fields.add(field_name)
    find_markers(data)
    undeclared_markers = marker_fields - uncertain_fields
    if undeclared_markers:
        uncertainty_errors.append(
            "[uncertain] values missing from uncertain array: " + ", ".join(sorted(undeclared_markers))
        )
    evidence_errors = validate_evidence(data, all_fields, required_fields, evidence_policy)
    covered = all_fields & json_fields
    missing = all_fields - json_fields
    extra = json_fields - all_fields
    missing_required = missing & required_fields
    missing_by_category = defaultdict(list)
    for field in missing:
        missing_by_category[field_categories.get(field, "Unknown")].append(field)
    return {
        "file": json_path.name,
        "total_defined": len(all_fields),
        "covered": len(covered),
        "missing": len(missing),
        "extra": len(extra),
        "coverage_rate": len(covered) / len(all_fields) * 100 if all_fields else 100,
        "missing_required": sorted(missing_required),
        "missing_optional": sorted(missing - required_fields),
        "missing_by_category": {k: sorted(v) for k, v in missing_by_category.items()},
        "extra_fields": sorted(extra),
        "uncertainty_errors": uncertainty_errors,
        "evidence_errors": evidence_errors,
        "valid": len(missing_required) == 0 and not uncertainty_errors and not evidence_errors,
    }


def print_result(result, verbose=True):
    status = "PASS" if result["valid"] else "FAIL"
    line = "=" * 60
    print(f"\n{line}")
    print(f"[{status}] {result['file']}")
    print(line)
    print(f"Coverage: {result['coverage_rate']:.1f}% ({result['covered']}/{result['total_defined']})")
    if result["missing_required"]:
        print(f"\n[ERROR] Missing required fields ({len(result['missing_required'])}):")
        print("\n".join(f"  - {f}" for f in result["missing_required"]))
    if result["uncertainty_errors"]:
        print(f"\n[ERROR] Uncertainty contract ({len(result['uncertainty_errors'])}):")
        print("\n".join(f"  - {message}" for message in result["uncertainty_errors"]))
    if result["evidence_errors"]:
        print(f"\n[ERROR] Evidence contract ({len(result['evidence_errors'])}):")
        print("\n".join(f"  - {message}" for message in result["evidence_errors"]))
    if verbose and result["missing_optional"]:
        missing_required = set(result["missing_required"])
        print(f"\n[WARN] Missing optional fields ({len(result['missing_optional'])}):")
        for cat in sorted(result["missing_by_category"]):
            optional = [f for f in result["missing_by_category"][cat] if f not in missing_required]
            if optional:
                print(f"  [{cat}]: {', '.join(optional)}")
    if verbose and result["extra_fields"]:
        extra = result["extra_fields"]
        print(f"\n[INFO] Extra fields ({len(extra)}):")
        print(f"  {', '.join(extra[:10])}")
        if len(extra) > 10:
            print(f"  ... and {len(extra) - 10} more")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate whether JSON files cover all fields defined in fields.yaml")
    parser.add_argument("--fields", "-f", type=str, help="Path to fields.yaml", default="fields.yaml")
    parser.add_argument("--json", "-j", type=str, nargs="*", help="JSON file paths to validate")
    parser.add_argument("--dir", "-d", type=str, help="Directory containing JSON files", default="results")
    parser.add_argument("--quiet", "-q", action="store_true", help="Show summary only")
    args = parser.parse_args()
    fields_path = Path(args.fields)
    if not fields_path.exists():
        for p in (Path.cwd() / "fields.yaml", Path.cwd().parent / "fields.yaml"):
            if p.exists():
                fields_path = p
                break
    if not fields_path.exists():
        print(f"[ERROR] fields.yaml not found: {fields_path}")
        sys.exit(1)
    print(f"Field definition file: {fields_path}")
    try:
        all_fields, required_fields, field_categories, evidence_policy = load_fields_yaml(fields_path)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Total fields: {len(all_fields)} (required: {len(required_fields)}, optional: {len(all_fields) - len(required_fields)})")
    json_files = (
        [Path(p) for p in args.json]
        if args.json
        else sorted(Path(args.dir).glob("*.json")) if Path(args.dir).exists() else []
    )
    if not json_files:
        print("[WARN] No JSON files found")
        sys.exit(0)
    results = []
    for json_path in json_files:
        if not json_path.exists():
            print(f"[WARN] File not found: {json_path}")
            continue
        result = validate_json(json_path, all_fields, required_fields, field_categories, evidence_policy)
        results.append(result)
        print_result(result, verbose=not args.quiet)
    line = "=" * 60
    print(f"\n{line}")
    print("Summary")
    print(line)
    passed = sum(1 for r in results if r["valid"])
    avg_coverage = sum(r["coverage_rate"] for r in results) / len(results) if results else 0
    print(f"Validation passed: {passed}/{len(results)}")
    print(f"Average coverage: {avg_coverage:.1f}%")
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
