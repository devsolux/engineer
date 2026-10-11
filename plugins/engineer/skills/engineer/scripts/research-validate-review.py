#!/usr/bin/env python3
"""Validate a hash-bound semantic review of deep-research claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

from research_contract import ResearchContractError, load_yaml_or_json, resolve_confined_file, resolve_regular_file, resolve_results_dir

LIMITATIONS = [
    "This receipt binds claims to reviewer-visible evidence excerpts; it does not prove that an excerpt faithfully represents its remote source.",
    "Reviewer names and independence are declarations, not cryptographic identity attestations.",
    "A passing review does not prove source availability, exhaustive retrieval, unbiased selection, or factual truth beyond the captured evidence.",
]
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
VERDICTS = {"supported", "partial", "unsupported", "unverifiable"}
METHODS = {"human", "model_assisted"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def safe_file(root: Path, value: object) -> Path | None:
    try:
        return resolve_regular_file(root, value, label="review artifact path")
    except ResearchContractError:
        return None


def iso_date(value: object) -> bool:
    try:
        return isinstance(value, str) and date.fromisoformat(value) <= date.today()
    except ValueError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--topic-dir", "-t", type=Path, required=True)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()
    root = args.topic_dir.resolve()
    errors: list[str] = []
    try:
        review_path = resolve_confined_file(root, args.review, label="review receipt")
    except ResearchContractError as exc:
        review_path = root / "__unsafe_review__"
        errors.append(str(exc))
    if errors:
        print("\n".join(f"[ERROR] {error}" for error in errors), file=sys.stderr)
        return 1
    try:
        data = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] invalid review JSON: {exc}", file=sys.stderr)
        return 1

    root_keys = {"schema_version", "receipt_kind", "topic", "artifacts", "items", "review", "decision", "limitations"}
    if not isinstance(data, dict) or set(data) != root_keys:
        errors.append("review receipt root keys are invalid")
        data = data if isinstance(data, dict) else {}
    if data.get("schema_version") != 1 or data.get("receipt_kind") != "research_claim_review":
        errors.append("review receipt identity is invalid")

    outline = root / "outline.yaml"
    fields = root / "fields.yaml"
    topic = data.get("topic") if isinstance(data.get("topic"), dict) else {}
    if set(topic) != {"outline_sha256", "fields_sha256", "as_of"}:
        errors.append("topic binding is invalid")
    else:
        for key, path in (("outline_sha256", outline), ("fields_sha256", fields)):
            if not path.is_file() or path.is_symlink() or (path.is_file() and topic.get(key) != digest(path)):
                errors.append(f"topic.{key} does not match current topic input")
    try:
        outline_data = load_yaml_or_json(outline)
    except (OSError, ValueError, json.JSONDecodeError):
        outline_data = {}
        errors.append("outline.yaml cannot be parsed for result confinement")
    try:
        results_dir = resolve_results_dir(root, outline_data)
        results_confined = True
    except ResearchContractError:
        results_dir = root / "__unsafe_results__"
        results_confined = False
        errors.append("configured results directory is missing or unsafe")
    result_prefix = results_dir.relative_to(root).as_posix().rstrip("/") + "/" if results_confined else ""

    artifacts = data.get("artifacts")
    artifact_map: dict[str, dict] = {}
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("artifacts must be a non-empty array")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        label = f"artifacts[{index}]"
        keys = {"id", "source_id", "source_url", "path", "sha256", "locator"}
        if not isinstance(artifact, dict) or set(artifact) != keys:
            errors.append(f"{label} shape is invalid")
            continue
        aid = artifact.get("id")
        path = safe_file(root, artifact.get("path"))
        if not isinstance(aid, str) or not TOKEN.fullmatch(aid) or aid in artifact_map:
            errors.append(f"{label}.id must be unique and non-empty")
        else:
            artifact_map[aid] = artifact
        if not all(text(artifact.get(key)) for key in ("source_id", "source_url", "locator")):
            errors.append(f"{label} source identity and locator are required")
        if path is None or not str(artifact.get("path", "")).startswith("evidence/") or not SHA256.fullmatch(str(artifact.get("sha256", ""))) or (path and digest(path) != artifact.get("sha256")):
            errors.append(f"{label} evidence file is unsafe, missing, or hash-mismatched")
        elif path.stat().st_size < 1 or path.stat().st_size > 32768:
            errors.append(f"{label} evidence excerpt must contain 1 to 32768 bytes")
        else:
            try:
                path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                errors.append(f"{label} evidence excerpt must be UTF-8 text")

    expected_claims: dict[tuple[str, str], dict] = {}
    result_sources: dict[tuple[str, str], dict] = {}
    for result_path in sorted(results_dir.glob("*.json")):
        if result_path.is_symlink() or not result_path.is_file():
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        rel = result_path.relative_to(root).as_posix()
        evidence = result.get("evidence") if isinstance(result, dict) else {}
        for source in evidence.get("sources", []) if isinstance(evidence, dict) else []:
            if isinstance(source, dict) and text(source.get("id")):
                result_sources[(rel, source["id"])] = source
        for claim in evidence.get("claims", []) if isinstance(evidence, dict) else []:
            if isinstance(claim, dict) and text(claim.get("id")):
                expected_claims[(rel, claim["id"])] = claim

    seen_claims: set[tuple[str, str]] = set()
    used_artifacts: set[str] = set()
    items = data.get("items")
    if not isinstance(items, list) or not items:
        errors.append("items must be a non-empty array")
        items = []
    for index, item in enumerate(items):
        label = f"items[{index}]"
        keys = {"result_path", "result_sha256", "name", "claims"}
        if not isinstance(item, dict) or set(item) != keys:
            errors.append(f"{label} shape is invalid")
            continue
        result_path = safe_file(root, item.get("result_path"))
        rel = item.get("result_path")
        if result_path is None or not str(rel).startswith(result_prefix) or digest(result_path) != item.get("result_sha256"):
            errors.append(f"{label} result binding is unsafe or stale")
            continue
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(f"{label} result JSON cannot be read")
            continue
        if not isinstance(result, dict):
            errors.append(f"{label} result must be an object")
            continue
        if item.get("name") != result.get("name"):
            errors.append(f"{label}.name does not match result")
        claims = item.get("claims")
        if not isinstance(claims, list) or not claims:
            errors.append(f"{label}.claims must be non-empty")
            continue
        for claim_index, reviewed in enumerate(claims):
            claim_label = f"{label}.claims[{claim_index}]"
            claim_keys = {"claim_id", "statement_sha256", "source_ids", "artifact_ids", "verdict", "rationale"}
            if not isinstance(reviewed, dict) or set(reviewed) != claim_keys:
                errors.append(f"{claim_label} shape is invalid")
                continue
            key = (str(rel), reviewed.get("claim_id"))
            original = expected_claims.get(key)
            if original is None or key in seen_claims:
                errors.append(f"{claim_label} references an unknown or duplicate claim")
                continue
            seen_claims.add(key)
            statement_sha = hashlib.sha256(original["statement"].encode()).hexdigest()
            if reviewed.get("statement_sha256") != statement_sha:
                errors.append(f"{claim_label} statement binding is stale")
            if reviewed.get("source_ids") != original.get("source_ids"):
                errors.append(f"{claim_label} source binding differs from the claim")
            artifact_ids = reviewed.get("artifact_ids")
            if not isinstance(artifact_ids, list) or not artifact_ids or len(artifact_ids) != len(set(artifact_ids)):
                errors.append(f"{claim_label}.artifact_ids must be a non-empty unique array")
                artifact_ids = []
            covered_sources = set()
            for aid in artifact_ids:
                artifact = artifact_map.get(aid)
                if artifact is None:
                    errors.append(f"{claim_label} references unknown artifact {aid}")
                    continue
                used_artifacts.add(aid)
                source = result_sources.get((str(rel), artifact.get("source_id")))
                if source is None or artifact.get("source_url") != source.get("url"):
                    errors.append(f"{claim_label} artifact source does not match result evidence")
                else:
                    covered_sources.add(artifact["source_id"])
            if set(original.get("source_ids", [])) != covered_sources:
                errors.append(f"{claim_label} captured evidence sources must exactly match cited sources")
            if reviewed.get("verdict") not in VERDICTS or not text(reviewed.get("rationale")):
                errors.append(f"{claim_label} verdict or rationale is invalid")

    if seen_claims != set(expected_claims):
        missing = sorted(f"{path}#{claim}" for path, claim in set(expected_claims) - seen_claims)
        errors.append("review does not cover every current claim: " + ", ".join(missing))
    if used_artifacts != set(artifact_map):
        errors.append("every captured evidence artifact must support at least one reviewed claim")

    review = data.get("review") if isinstance(data.get("review"), dict) else {}
    if set(review) != {"researcher", "reviewer", "method", "reviewed_at", "approved"}:
        errors.append("review declaration is invalid")
    elif not all(text(review.get(key)) for key in ("researcher", "reviewer")) or review.get("researcher") == review.get("reviewer") or review.get("method") not in METHODS or not iso_date(review.get("reviewed_at")) or not isinstance(review.get("approved"), bool):
        errors.append("review must declare distinct roles, method, valid date, and approval")
    verdicts = [claim.get("verdict") for item in items if isinstance(item, dict) for claim in item.get("claims", []) if isinstance(claim, dict)]
    expected_pass = bool(verdicts) and all(verdict == "supported" for verdict in verdicts) and review.get("approved") is True
    decision = data.get("decision")
    if decision not in {"pass", "fail"} or (decision == "pass") != expected_pass:
        errors.append("decision must be derived from supported verdicts and reviewer approval")
    if data.get("limitations") != LIMITATIONS:
        errors.append("mandatory semantic-review limitations are missing or altered")
    try:
        outline_as_of = outline_data.get("as_of")
    except (OSError, ValueError, json.JSONDecodeError):
        outline_as_of = None
    if topic.get("as_of") != outline_as_of:
        errors.append("topic.as_of does not match outline.as_of")
    elif isinstance(outline_as_of, str) and iso_date(review.get("reviewed_at")) and review.get("reviewed_at") < outline_as_of:
        errors.append("review.reviewed_at cannot precede the research cutoff")

    if errors:
        print("\n".join(f"[ERROR] {error}" for error in errors), file=sys.stderr)
        return 1
    if not args.quiet:
        print(f"research semantic review valid ({len(seen_claims)} claim(s), decision={decision})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
