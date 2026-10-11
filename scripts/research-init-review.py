#!/usr/bin/env python3
"""Create a non-authorizing semantic-review draft from current research results."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

from research_contract import ResearchContractError, load_yaml_or_json, resolve_confined_file, resolve_regular_file, resolve_results_dir

LIMITATIONS = [
    "This receipt binds claims to reviewer-visible evidence excerpts; it does not prove that an excerpt faithfully represents its remote source.",
    "Reviewer names and independence are declarations, not cryptographic identity attestations.",
    "A passing review does not prove source availability, exhaustive retrieval, unbiased selection, or factual truth beyond the captured evidence.",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topic-dir", "-t", type=Path, required=True)
    parser.add_argument("--researcher", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--method", choices=("human", "model_assisted"), default="human")
    parser.add_argument("--reviewed-at", default=date.today().isoformat())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.topic_dir.resolve()
    outline_path = root / "outline.yaml"
    fields_path = root / "fields.yaml"
    if args.researcher.strip() == args.reviewer.strip() or not args.researcher.strip() or not args.reviewer.strip():
        print("researcher and reviewer must be distinct non-empty identities", file=sys.stderr)
        return 2
    try:
        reviewed_at = date.fromisoformat(args.reviewed_at)
    except ValueError:
        print("reviewed-at must be an ISO date", file=sys.stderr)
        return 2
    if reviewed_at > date.today():
        print("reviewed-at cannot be in the future", file=sys.stderr)
        return 2
    try:
        resolve_regular_file(root, "outline.yaml", label="outline.yaml")
        resolve_regular_file(root, "fields.yaml", label="fields.yaml")
    except ResearchContractError:
        print("topic requires regular confined outline.yaml and fields.yaml", file=sys.stderr)
        return 2
    try:
        outline = load_yaml_or_json(outline_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"invalid outline: {exc}", file=sys.stderr)
        return 2
    output_value = args.output or Path("review.json")
    if output_value.is_absolute():
        try:
            output_value = output_value.relative_to(args.topic_dir.absolute())
        except ValueError:
            pass
    try:
        output = resolve_confined_file(root, output_value, label="review output", require_exists=False)
    except ResearchContractError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if output.exists() or output.is_symlink():
        print("refusing to overwrite existing review draft", file=sys.stderr)
        return 2

    items = []
    try:
        results_dir = resolve_results_dir(root, outline)
    except ResearchContractError:
        print("results directory is missing or unsafe", file=sys.stderr)
        return 2
    for path in sorted(results_dir.glob("*.json")):
        try:
            path = resolve_regular_file(results_dir, path.name, label=f"result {path.name}")
        except ResearchContractError:
            print(f"unsafe result path: {path}", file=sys.stderr)
            return 2
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"invalid result {path.name}: {exc}", file=sys.stderr)
            return 2
        evidence = result.get("evidence") if isinstance(result, dict) else None
        claims = evidence.get("claims") if isinstance(evidence, dict) else None
        if not isinstance(result, dict) or not isinstance(claims, list) or not claims:
            print(f"result lacks claim evidence: {path.name}", file=sys.stderr)
            return 2
        reviewed_claims = []
        for claim in claims:
            statement = claim.get("statement") if isinstance(claim, dict) else None
            if not isinstance(statement, str):
                print(f"result has malformed claim: {path.name}", file=sys.stderr)
                return 2
            reviewed_claims.append({
                "claim_id": claim.get("id"),
                "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
                "source_ids": claim.get("source_ids"),
                "artifact_ids": [],
                "verdict": "unverifiable",
                "rationale": "Pending independent evidence review.",
            })
        items.append({
            "result_path": path.relative_to(root).as_posix(),
            "result_sha256": digest(path),
            "name": result.get("name"),
            "claims": reviewed_claims,
        })
    if not items:
        print("no result JSON files found", file=sys.stderr)
        return 2
    draft = {
        "schema_version": 1,
        "receipt_kind": "research_claim_review",
        "topic": {"outline_sha256": digest(outline_path), "fields_sha256": digest(fields_path), "as_of": outline.get("as_of")},
        "artifacts": [],
        "items": items,
        "review": {"researcher": args.researcher, "reviewer": args.reviewer, "method": args.method, "reviewed_at": args.reviewed_at, "approved": False},
        "decision": "fail",
        "limitations": LIMITATIONS,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    print(f"wrote non-authorizing review draft: {output} ({sum(len(item['claims']) for item in items)} claim(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
