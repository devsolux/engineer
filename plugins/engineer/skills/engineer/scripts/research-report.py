#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate markdown report from deep-research results.

Usage:
  python3 scripts/research-report.py --topic-dir ./my-topic
  python3 scripts/research-report.py --topic-dir ./my-topic --toc-fields github_stars,license

Skips values containing [uncertain] and fields listed in each JSON's uncertain array.
Supports flat or nested (category-keyed) JSON. Adapted for engineer deep-research module.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from research_contract import ResearchContractError, load_yaml_or_json, resolve_results_dir

# Top-level keys that are categories, not leaf fields
_NEST_HINTS = {
    "basic_info",
    "Basic Info",
    "technical_features",
    "technical_characteristics",
    "Technical Features",
    "performance_metrics",
    "performance",
    "Performance Metrics",
    "milestone_significance",
    "milestones",
    "Milestone Significance",
    "business_info",
    "commercial_info",
    "Business Info",
    "competition_ecosystem",
    "competition",
    "Competition & Ecosystem",
    "history",
    "History",
    "market_positioning",
    "market",
    "Market Positioning",
    "engineering_fit",
    "Engineering Fit",
    "operations",
    "Operations",
    "maturity_risk",
    "Maturity & Risk",
    "decision",
    "Decision",
    "product",
    "Product",
    "technical_stack_public",
    "Technical Stack (public)",
    "gtm_traction",
    "GTM & Traction",
    "competitive_notes",
    "Competitive Notes",
    "threat_control",
    "Threat / Control",
    "implementation",
    "Implementation",
    "compliance_linkage",
    "Compliance Linkage",
    "product_fit",
    "Product Fit",
    "technical",
    "Technical",
    "ops_cost",
    "Ops & Cost",
}

_SKIP = {"_source_file", "uncertain", "evidence"}


def slug_anchor(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "item"


def load_fields(fields_path: Path) -> list[tuple[str, str, list[dict]]]:
    """Return list of (category_name, category_key_guess, fields[{name,description}])."""
    data = load_yaml_or_json(fields_path)
    out = []
    for cat in data.get("field_categories") or []:
        cname = cat.get("category") or "Other"
        fields = cat.get("fields") or []
        out.append((cname, cname, fields))
    return out


def flatten_item(data: dict) -> dict[str, Any]:
    """Merge nested category dicts into a flat field map."""
    flat: dict[str, Any] = {}
    for k, v in data.items():
        if k in _SKIP:
            continue
        if isinstance(v, dict) and (k in _NEST_HINTS or any(isinstance(x, (str, int, float, list, dict, type(None))) for x in v.values())):
            # If all values look like fields (not a single scalar wrapper), nest-merge
            if k in _NEST_HINTS or all(not isinstance(x, dict) or True for x in v.values()):
                for fk, fv in v.items():
                    if fk not in _SKIP:
                        flat[fk] = fv
                continue
        flat[k] = v
    return flat


def is_uncertain_value(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        s = val.strip()
        if not s or "[uncertain]" in s.lower():
            return True
    return False


def fmt_value(val: Any) -> str:
    if isinstance(val, list):
        if not val:
            return ""
        if all(isinstance(x, dict) for x in val):
            lines = []
            for item in val:
                parts = [f"{k}: {v}" for k, v in item.items()]
                lines.append("- " + " | ".join(parts))
            return "\n" + "\n".join(lines)
        if all(isinstance(x, str) for x in val) and sum(len(x) for x in val) < 120:
            return ", ".join(val)
        return "\n" + "\n".join(f"- {x}" for x in val)
    if isinstance(val, dict):
        return "; ".join(f"{k}: {v}" for k, v in val.items())
    s = str(val)
    if len(s) > 200:
        return s
    return s


def find_field(flat: dict, name: str) -> Any:
    if name in flat:
        return flat[name]
    # case-insensitive
    low = {k.lower(): v for k, v in flat.items()}
    return low.get(name.lower())


def main() -> int:
    ap = argparse.ArgumentParser(description="Deep-research results → report.md")
    ap.add_argument("--topic-dir", "-t", required=True, help="Directory with outline.yaml, fields.yaml, results/")
    ap.add_argument("--toc-fields", default="", help="Comma-separated field names for TOC columns")
    ap.add_argument("--out", default="", help="Output path (default: {topic-dir}/report.md)")
    args = ap.parse_args()

    root = Path(args.topic_dir).resolve()
    outline_path = root / "outline.yaml"
    fields_path = root / "fields.yaml"
    if not outline_path.exists():
        print(f"[ERROR] missing {outline_path}", file=sys.stderr)
        return 1
    if not fields_path.exists():
        print(f"[ERROR] missing {fields_path}", file=sys.stderr)
        return 1

    try:
        outline = load_yaml_or_json(outline_path)
    except (ResearchContractError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    topic = outline.get("topic") or root.name
    try:
        results_dir = resolve_results_dir(root, outline)
    except ResearchContractError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    try:
        categories = load_fields(fields_path)
        field_contract = load_yaml_or_json(fields_path)
    except (ResearchContractError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    toc_fields = [f.strip() for f in args.toc_fields.split(",") if f.strip()]
    json_files = sorted(results_dir.glob("*.json"))
    if not json_files:
        print(f"[ERROR] no JSON in {results_dir}", file=sys.stderr)
        return 1

    validator = Path(__file__).with_name("research-validate-topic.py")
    validation = subprocess.run(
        [sys.executable, str(validator), "--quiet", "--topic-dir", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    if validation.returncode:
        print("[ERROR] research evidence validation failed; report not generated", file=sys.stderr)
        if validation.stdout:
            print(validation.stdout.rstrip(), file=sys.stderr)
        if validation.stderr:
            print(validation.stderr.rstrip(), file=sys.stderr)
        return 1

    items: list[tuple[str, dict, dict]] = []
    for jp in json_files:
        data = json.loads(jp.read_text(encoding="utf-8"))
        flat = flatten_item(data)
        name = flat.get("name") or jp.stem.replace("_", " ")
        uncertain = set(data.get("uncertain") or [])
        items.append((str(name), flat, {"uncertain": uncertain, "file": jp.name, "evidence": data.get("evidence")}))

    lines: list[str] = []
    lines.append(f"# {topic}")
    lines.append("")
    lines.append(f"_Generated by engineer deep-research · {len(items)} items · sources in each section_")
    lines.append("")
    evidence_policy = field_contract.get("evidence_policy") if isinstance(field_contract.get("evidence_policy"), dict) else {}
    if evidence_policy.get("semantic_review") == "required":
        lines.append("_Claim support: independently reviewed against captured evidence; see `review.json` and its limitations._")
    else:
        lines.append("_Claim support: no semantic review was required; source links and structural validation do not prove support._")
    lines.append("")
    lines.append("## Table of contents")
    lines.append("")
    for i, (name, flat, meta) in enumerate(items, 1):
        anchor = slug_anchor(name)
        extra = []
        for f in toc_fields:
            v = find_field(flat, f)
            if v is not None and not is_uncertain_value(v) and f not in meta["uncertain"]:
                extra.append(f"{f}: {v}")
        suffix = (" — " + " · ".join(str(x) for x in extra)) if extra else ""
        lines.append(f"{i}. [{name}](#{anchor}){suffix}")
    lines.append("")

    for name, flat, meta in items:
        lines.append(f"## {name}")
        lines.append("")
        # Group by fields.yaml categories
        used: set[str] = set()
        for cname, _, fields in categories:
            block: list[str] = []
            for fd in fields:
                fname = fd.get("name")
                if not fname:
                    continue
                if fname in meta["uncertain"]:
                    continue
                val = find_field(flat, fname)
                if is_uncertain_value(val):
                    continue
                used.add(fname)
                desc = fd.get("description") or ""
                formatted = fmt_value(val)
                if "\n" in formatted:
                    block.append(f"**{fname}**" + (f" _{desc}_" if desc else "") + f":\n{formatted}")
                else:
                    block.append(f"- **{fname}**: {formatted}")
            if block:
                lines.append(f"### {cname}")
                lines.append("")
                lines.extend(block)
                lines.append("")
        # Extra fields not in schema
        extras = []
        for k, v in flat.items():
            if k in used or k in meta["uncertain"] or k in _SKIP:
                continue
            if is_uncertain_value(v):
                continue
            extras.append(f"- **{k}**: {fmt_value(v)}")
        if extras:
            lines.append("### Other")
            lines.append("")
            lines.extend(extras)
            lines.append("")
        if meta["uncertain"]:
            lines.append("### Uncertain fields")
            lines.append("")
        evidence = meta.get("evidence")
        if isinstance(evidence, dict) and evidence.get("sources"):
            lines.append("### Evidence")
            lines.append("")
            lines.append(f"Research as of: {evidence.get('as_of', 'unknown')}")
            lines.append("")
            for source in evidence["sources"]:
                lines.append(f"- [{source.get('title', source.get('id'))}]({source.get('url')}) - {source.get('publisher', 'unknown')} ({source.get('source_type', 'unknown')}, accessed {source.get('accessed_at', 'unknown')})")
            lines.append("")
            for u in sorted(meta["uncertain"]):
                lines.append(f"- {u}")
            lines.append("")

    out = Path(args.out) if args.out else root / "report.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out} ({len(items)} items)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
