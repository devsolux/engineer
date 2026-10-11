#!/usr/bin/env bash
# Fixture tests for deep-research validation and report generation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PY=(python3)

mkdir -p "$TMP/topic/results"
# JSON is valid YAML. The offline health path must not download dependencies.
# CI installs PyYAML and exercises these through the YAML parser.
cat > "$TMP/topic/fields.yaml" <<'JSON'
{"evidence_policy":{"mode":"claim_v1","semantic_review":"required","identity_fields":["name","sources"]},"field_categories":[{"category":"Basic Info","fields":[{"name":"name","required":true},{"name":"license","required":true},{"name":"sources","required":true}]}]}
JSON
cat > "$TMP/topic/outline.yaml" <<'JSON'
{"topic":"Research fixture","as_of":"2026-07-15","items":[{"name":"Fixture"}],"execution":{"output_dir":"./results"}}
JSON
cat > "$TMP/topic/results/valid.json" <<'JSON'
{"name":"Fixture","license":"MIT","sources":[{"title":"Primary","url":"https://example.test/docs","accessed_at":"2026-07-15"}],"evidence":{"as_of":"2026-07-15","sources":[{"id":"official_docs","title":"Primary","url":"https://example.test/docs","publisher":"Fixture Org","source_type":"official_docs","accessed_at":"2026-07-15"}],"claims":[{"id":"license_claim","field":"license","statement":"The project uses the MIT license.","kind":"fact","confidence":"high","source_ids":["official_docs"]}]},"uncertain":[]}
JSON
cat > "$TMP/topic/results/invalid.json" <<'JSON'
{"name":"Broken","uncertain":[]}
JSON
cat > "$TMP/topic/results/invalid-uncertain.json" <<'JSON'
{"name":"Unclear","license":"[uncertain]","sources":[],"uncertain":[]}
JSON
cat > "$TMP/topic/results/invalid-evidence.json" <<'JSON'
{"name":"Forged","license":"MIT","sources":[],"evidence":{"as_of":"2026-07-15","sources":[{"id":"bad","title":"Bad","url":"https://user:secret@example.test/docs#claim","publisher":"Unknown","source_type":"blog","accessed_at":"2026-07-16"}],"claims":[{"id":"license_claim","field":"license","statement":"The project uses MIT.","kind":"fact","confidence":"certain","source_ids":["missing"]}]},"uncertain":[]}
JSON
mkdir -p "$TMP/topic/evidence"
printf '%s\n' 'License: MIT' > "$TMP/topic/evidence/license.txt"
python3 - "$TMP/topic" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
statement = "The project uses the MIT license."
review = {
    "schema_version": 1,
    "receipt_kind": "research_claim_review",
    "topic": {"outline_sha256": sha(root / "outline.yaml"), "fields_sha256": sha(root / "fields.yaml"), "as_of": "2026-07-15"},
    "artifacts": [{"id": "license_excerpt", "source_id": "official_docs", "source_url": "https://example.test/docs", "path": "evidence/license.txt", "sha256": sha(root / "evidence/license.txt"), "locator": "License declaration"}],
    "items": [{"result_path": "results/valid.json", "result_sha256": sha(root / "results/valid.json"), "name": "Fixture", "claims": [{"claim_id": "license_claim", "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(), "source_ids": ["official_docs"], "artifact_ids": ["license_excerpt"], "verdict": "supported", "rationale": "The captured declaration names the MIT license."}]}],
    "review": {"researcher": "fixture-researcher", "reviewer": "fixture-reviewer", "method": "human", "reviewed_at": "2026-07-15", "approved": True},
    "decision": "pass",
    "limitations": [
        "This receipt binds claims to reviewer-visible evidence excerpts; it does not prove that an excerpt faithfully represents its remote source.",
        "Reviewer names and independence are declarations, not cryptographic identity attestations.",
        "A passing review does not prove source availability, exhaustive retrieval, unbiased selection, or factual truth beyond the captured evidence.",
    ],
}
(root / "review.json").write_text(json.dumps(review), encoding="utf-8")
PY

echo "engineer test-research — fixtures"
echo "---"
"${PY[@]}" "$ROOT/scripts/research-validate-json.py" -q -f "$TMP/topic/fields.yaml" -j "$TMP/topic/results/valid.json" >/dev/null
echo "  ✓ valid result accepted"

cp -R "$TMP/topic" "$TMP/valid_topic"
rm "$TMP/valid_topic/results/invalid.json" "$TMP/valid_topic/results/invalid-uncertain.json" "$TMP/valid_topic/results/invalid-evidence.json"
"${PY[@]}" "$ROOT/scripts/research-validate-topic.py" -q -t "$TMP/valid_topic" >/dev/null
cp -R "$TMP/valid_topic" "$TMP/draft_topic"
rm "$TMP/draft_topic/review.json"
"${PY[@]}" "$ROOT/scripts/research-init-review.py" -t "$TMP/draft_topic" --researcher fixture-researcher --reviewer fixture-reviewer >/dev/null
grep -q '"decision": "fail"' "$TMP/draft_topic/review.json"
if "${PY[@]}" "$ROOT/scripts/research-validate-review.py" -q -t "$TMP/draft_topic" "$TMP/draft_topic/review.json" >/dev/null 2>&1; then
  echo "  ✗ non-authorizing review draft unexpectedly passed"
  exit 1
fi
if "${PY[@]}" "$ROOT/scripts/research-init-review.py" -t "$TMP/draft_topic" --researcher fixture-researcher --reviewer fixture-reviewer >/dev/null 2>&1; then
  echo "  ✗ review draft initializer unexpectedly overwrote an existing receipt"
  exit 1
fi
rm -rf "${TMP:?}/draft_topic"
echo "  ✓ review draft derives bindings without authorizing publication"

cp -R "$TMP/valid_topic" "$TMP/absolute_draft_topic"
rm "$TMP/absolute_draft_topic/review.json"
"${PY[@]}" "$ROOT/scripts/research-init-review.py" -t "$TMP/absolute_draft_topic" --researcher fixture-researcher --reviewer fixture-reviewer --output "$TMP/absolute_draft_topic/nested/review.json" >/dev/null
test -f "$TMP/absolute_draft_topic/nested/review.json"
rm -rf "${TMP:?}/absolute_draft_topic"

invalid_topic_case() {
  local name="$1"
  local mutation="$2"
  cp -R "$TMP/valid_topic" "$TMP/$name"
  eval "$mutation"
  if "${PY[@]}" "$ROOT/scripts/research-validate-topic.py" -q -t "$TMP/$name" >/dev/null 2>&1; then
    echo "  ✗ $name topic unexpectedly accepted"
    exit 1
  fi
  rm -rf "${TMP:?}/$name"
}

invalid_topic_case missing_item "python3 -c \"import json; p=json.load(open('$TMP/missing_item/outline.yaml')); p['items'].append({'name':'Missing'}); json.dump(p,open('$TMP/missing_item/outline.yaml','w'))\""
invalid_topic_case extra_item "python3 -c \"import json; p=json.load(open('$TMP/extra_item/results/valid.json')); p['name']='Extra'; json.dump(p,open('$TMP/extra_item/results/extra.json','w'))\""
invalid_topic_case duplicate_item "cp '$TMP/duplicate_item/results/valid.json' '$TMP/duplicate_item/results/duplicate.json'"
invalid_topic_case cutoff_drift "python3 -c \"import json; p=json.load(open('$TMP/cutoff_drift/results/valid.json')); p['evidence']['as_of']='2026-07-14'; json.dump(p,open('$TMP/cutoff_drift/results/valid.json','w'))\""
invalid_topic_case output_escape "python3 -c \"import json; p=json.load(open('$TMP/output_escape/outline.yaml')); p['execution']['output_dir']='../results'; json.dump(p,open('$TMP/output_escape/outline.yaml','w'))\""
invalid_topic_case output_root "python3 -c \"import json; p=json.load(open('$TMP/output_root/outline.yaml')); p['execution']['output_dir']='.'; json.dump(p,open('$TMP/output_root/outline.yaml','w'))\""
invalid_topic_case result_symlink "ln -s valid.json '$TMP/result_symlink/results/linked.json'"
invalid_topic_case source_conflict "python3 -c \"import json; o=json.load(open('$TMP/source_conflict/outline.yaml')); o['items'].append({'name':'Other'}); json.dump(o,open('$TMP/source_conflict/outline.yaml','w')); p=json.load(open('$TMP/source_conflict/results/valid.json')); p['name']='Other'; p['evidence']['sources'][0]['publisher']='Conflicting Org'; json.dump(p,open('$TMP/source_conflict/results/other.json','w'))\""
invalid_topic_case missing_review "rm '$TMP/missing_review/review.json'"
invalid_topic_case stale_review "python3 -c \"import json; p=json.load(open('$TMP/stale_review/review.json')); p['items'][0]['claims'][0]['statement_sha256']='0'*64; json.dump(p,open('$TMP/stale_review/review.json','w'))\""
invalid_topic_case unsupported_claim "python3 -c \"import json; p=json.load(open('$TMP/unsupported_claim/review.json')); p['items'][0]['claims'][0]['verdict']='partial'; p['decision']='fail'; json.dump(p,open('$TMP/unsupported_claim/review.json','w'))\""
invalid_topic_case evidence_tamper "printf '%s\n' 'License: Apache-2.0' > '$TMP/evidence_tamper/evidence/license.txt'"
invalid_topic_case evidence_symlink "rm '$TMP/evidence_symlink/evidence/license.txt'; ln -s '../results/valid.json' '$TMP/evidence_symlink/evidence/license.txt'"
invalid_topic_case review_receipt_symlink "mv '$TMP/review_receipt_symlink/review.json' '$TMP/review_receipt_symlink/review-real.json'; ln -s review-real.json '$TMP/review_receipt_symlink/review.json'"
invalid_topic_case source_mismatch "python3 -c \"import json; p=json.load(open('$TMP/source_mismatch/review.json')); p['artifacts'][0]['source_url']='https://example.test/other'; json.dump(p,open('$TMP/source_mismatch/review.json','w'))\""
invalid_topic_case unused_artifact "python3 -c \"import json; p=json.load(open('$TMP/unused_artifact/review.json')); q=dict(p['artifacts'][0]); q['id']='unused_excerpt'; p['artifacts'].append(q); json.dump(p,open('$TMP/unused_artifact/review.json','w'))\""
invalid_topic_case extra_source_artifact "python3 -c \"import hashlib,json; rp='$TMP/extra_source_artifact/results/valid.json'; p=json.load(open(rp)); q=dict(p['evidence']['sources'][0]); q['id']='secondary_docs'; p['evidence']['sources'].append(q); json.dump(p,open(rp,'w')); rv='$TMP/extra_source_artifact/review.json'; r=json.load(open(rv)); r['items'][0]['result_sha256']=hashlib.sha256(open(rp,'rb').read()).hexdigest(); a=dict(r['artifacts'][0]); a['id']='extra_excerpt'; a['source_id']='secondary_docs'; r['artifacts'].append(a); r['items'][0]['claims'][0]['artifact_ids'].append('extra_excerpt'); json.dump(r,open(rv,'w'))\""
invalid_topic_case same_reviewer "python3 -c \"import json; p=json.load(open('$TMP/same_reviewer/review.json')); p['review']['reviewer']=p['review']['researcher']; json.dump(p,open('$TMP/same_reviewer/review.json','w'))\""
echo "  ✓ topic coverage, cutoff, confinement, identity, and exact source binding enforced"

cp -R "$TMP/valid_topic" "$TMP/custom_output"
mv "$TMP/custom_output/results" "$TMP/custom_output/deep-results"
python3 - "$TMP/custom_output" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
outline = json.loads((root / "outline.yaml").read_text())
outline["execution"]["output_dir"] = "./deep-results"
(root / "outline.yaml").write_text(json.dumps(outline))
review = json.loads((root / "review.json").read_text())
review["topic"]["outline_sha256"] = hashlib.sha256((root / "outline.yaml").read_bytes()).hexdigest()
review["items"][0]["result_path"] = "deep-results/valid.json"
(root / "review.json").write_text(json.dumps(review))
PY
"${PY[@]}" "$ROOT/scripts/research-validate-topic.py" -q -t "$TMP/custom_output" >/dev/null
"${PY[@]}" "$ROOT/scripts/research-report.py" -t "$TMP/custom_output" >/dev/null
echo "  ✓ configured custom result directory compiles, reviews, and reports"

cp -R "$TMP/valid_topic" "$TMP/symlink_draft_output"
rm "$TMP/symlink_draft_output/review.json"
mkdir "$TMP/symlink_draft_output/real-output"
ln -s real-output "$TMP/symlink_draft_output/linked-output"
if "${PY[@]}" "$ROOT/scripts/research-init-review.py" -t "$TMP/symlink_draft_output" --researcher fixture-researcher --reviewer fixture-reviewer --output linked-output/review.json >/dev/null 2>&1; then
  echo "  ✗ review initializer wrote through a symlinked output parent"
  exit 1
fi
test ! -f "$TMP/symlink_draft_output/real-output/review.json"
echo "  ✓ review receipts and draft outputs reject symlink components"

cp -R "$TMP/valid_topic" "$TMP/symlink_parent"
mkdir -p "$TMP/symlink_parent/real-parent"
mv "$TMP/symlink_parent/results" "$TMP/symlink_parent/real-parent/results"
ln -s real-parent "$TMP/symlink_parent/linked-parent"
python3 - "$TMP/symlink_parent" <<'PY'
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
outline = json.loads((root / "outline.yaml").read_text())
outline["execution"]["output_dir"] = "./linked-parent/results"
(root / "outline.yaml").write_text(json.dumps(outline))
review = json.loads((root / "review.json").read_text())
review["topic"]["outline_sha256"] = hashlib.sha256((root / "outline.yaml").read_bytes()).hexdigest()
review["items"][0]["result_path"] = "linked-parent/results/valid.json"
(root / "review.json").write_text(json.dumps(review))
PY
for command in \
  "research-validate-topic.py -q -t $TMP/symlink_parent" \
  "research-validate-review.py -q -t $TMP/symlink_parent $TMP/symlink_parent/review.json" \
  "research-report.py -t $TMP/symlink_parent"; do
  read -r -a parts <<< "$command"
  if "${PY[@]}" "$ROOT/scripts/${parts[0]}" "${parts[@]:1}" >/dev/null 2>&1; then
    echo "  ✗ ${parts[0]} accepted a symlinked output parent"
    exit 1
  fi
done
cp -R "$TMP/symlink_parent" "$TMP/symlink_parent_draft"
rm "$TMP/symlink_parent_draft/review.json"
if "${PY[@]}" "$ROOT/scripts/research-init-review.py" -t "$TMP/symlink_parent_draft" --researcher fixture-researcher --reviewer fixture-reviewer >/dev/null 2>&1; then
  echo "  ✗ research-init-review.py accepted a symlinked output parent"
  exit 1
fi

cp -R "$TMP/valid_topic" "$TMP/no_fallback"
python3 -c "import json; p=json.load(open('$TMP/no_fallback/outline.yaml')); p['execution']['output_dir']='./missing-results'; json.dump(p,open('$TMP/no_fallback/outline.yaml','w'))"
if "${PY[@]}" "$ROOT/scripts/research-report.py" -t "$TMP/no_fallback" >/dev/null 2>&1; then
  echo "  ✗ report silently fell back from the configured output directory"
  exit 1
fi
test ! -f "$TMP/no_fallback/report.md"
echo "  ✓ all callers reject nested symlinks and report never falls back"

invalid_evidence_case() {
  local name="$1"
  local mutation="$2"
  python3 -c "import json; p=json.load(open('$TMP/topic/results/valid.json')); $mutation; json.dump(p,open('$TMP/topic/results/$name.json','w'))"
  if "${PY[@]}" "$ROOT/scripts/research-validate-json.py" -q -f "$TMP/topic/fields.yaml" -j "$TMP/topic/results/$name.json" >/dev/null 2>&1; then
    echo "  ✗ $name evidence unexpectedly accepted"
    exit 1
  fi
  rm "$TMP/topic/results/$name.json"
}

invalid_evidence_case unknown_source "p['evidence']['claims'][0]['source_ids']=['missing']"
invalid_evidence_case missing_claim "p['evidence']['claims']=[]"
invalid_evidence_case future_access "p['evidence']['sources'][0]['accessed_at']='2099-01-01'"
invalid_evidence_case credential_url "p['evidence']['sources'][0]['url']='https://user:secret@example.test/docs'"
invalid_evidence_case duplicate_source "p['evidence']['sources'].append(dict(p['evidence']['sources'][0]))"
invalid_evidence_case unsupported_kind "p['evidence']['claims'][0]['kind']='opinion'"
echo "  ✓ isolated evidence mutations rejected"
if "${PY[@]}" "$ROOT/scripts/research-validate-json.py" -q -f "$TMP/topic/fields.yaml" -j "$TMP/topic/results/invalid.json" >/dev/null 2>&1; then
  echo "  ✗ invalid result unexpectedly accepted"
  exit 1
fi
echo "  ✓ missing required fields rejected"
if "${PY[@]}" "$ROOT/scripts/research-validate-json.py" -q -f "$TMP/topic/fields.yaml" -j "$TMP/topic/results/invalid-uncertain.json" >/dev/null 2>&1; then
  echo "  ✗ undeclared uncertain marker unexpectedly accepted"
  exit 1
fi
echo "  ✓ uncertainty contract enforced"
if "${PY[@]}" "$ROOT/scripts/research-validate-json.py" -q -f "$TMP/topic/fields.yaml" -j "$TMP/topic/results/invalid-evidence.json" >/dev/null 2>&1; then
  echo "  ✗ invalid evidence unexpectedly accepted"
  exit 1
fi
echo "  ✓ claim/source/date/URL evidence contract enforced"
if "${PY[@]}" "$ROOT/scripts/research-report.py" --topic-dir "$TMP/topic" --toc-fields license >/dev/null 2>&1; then
  echo "  ✗ report unexpectedly bypassed invalid item evidence"
  exit 1
fi
test ! -f "$TMP/topic/report.md"
echo "  ✓ report publication blocks invalid item evidence"
rm "$TMP/topic/results/invalid.json" "$TMP/topic/results/invalid-uncertain.json" "$TMP/topic/results/invalid-evidence.json"
"${PY[@]}" "$ROOT/scripts/research-report.py" --topic-dir "$TMP/topic" --toc-fields license >/dev/null
grep -q '^# Research fixture' "$TMP/topic/report.md"
grep -q 'license: MIT' "$TMP/topic/report.md"
grep -q 'https://example.test/docs' "$TMP/topic/report.md"
grep -q '^### Evidence' "$TMP/topic/report.md"
grep -q '^_Claim support: independently reviewed' "$TMP/topic/report.md"
echo "  ✓ deterministic report generated with sources"
echo "---"
echo "OK — all research fixture tests passed"
