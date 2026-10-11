#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

cases=(
  "validate-agentic-contract.py:execution-contract.sample.json"
  "validate-agent-incident.py:agent-incident.sample.json"
  "validate-agent-memory.py:agent-memory.sample.json"
  "validate-agentic-completion.py:completion-receipt.sample.json"
  "validate-browser-session.py:browser-session.sample.json"
  "validate-capability-promotion.py:capability-promotion.sample.json"
  "validate-coordination-envelope.py:coordination-envelope.sample.json"
  "validate-host-capabilities.py:host-capabilities.sample.json"
  "validate-mcp-content.py:mcp-content.sample.json"
  "validate-mcp-session.py:mcp-session.sample.json"
  "validate-orchestration-contract.py:orchestration-contract.sample.json"
  "validate-orchestration-run.py:orchestration-run.sample.json"
)

for item in "${cases[@]}"; do
  validator="${item%%:*}"
  sample="${item#*:}"
  link="$TMP/$sample"
  ln -s "$ROOT/templates/agentic/$sample" "$link"
  if python3 "$ROOT/scripts/$validator" "$link" >/dev/null 2>"$TMP/error"; then
    echo "$validator accepted a symlinked top-level input" >&2
    exit 1
  fi
  if ! grep -q 'regular file, not a symlink' "$TMP/error"; then
    echo "$validator rejected for the wrong reason" >&2
    cat "$TMP/error" >&2
    exit 1
  fi
done

expect_reject() {
  local name="$1" source="$2"
  shift 2
  local link="$TMP/$name"
  ln -s "$ROOT/$source" "$link"
  if "$@" "$link" >"$TMP/output" 2>"$TMP/error"; then
    echo "$name accepted a symlinked top-level input" >&2
    exit 1
  fi
  if ! grep -q 'regular file, not a symlink' "$TMP/error" "$TMP/output"; then
    echo "$name rejected for the wrong reason" >&2
    cat "$TMP/error" >&2
    exit 1
  fi
}

expect_reject capture-job-link.json templates/agentic/skill-eval-job.sample.json \
  python3 "$ROOT/scripts/capture-skill-eval.py" --print-command
expect_reject telemetry-record-link.json templates/agentic/skill-eval-capture.sample.json \
  python3 "$ROOT/scripts/record-engineer-telemetry.py"
expect_reject telemetry-summary-link.jsonl templates/agentic/engineer-telemetry.sample.jsonl \
  python3 "$ROOT/scripts/summarize-engineer-telemetry.py"
expect_reject telemetry-validate-link.jsonl templates/agentic/engineer-telemetry.sample.jsonl \
  python3 "$ROOT/scripts/validate-engineer-telemetry.py"
expect_reject optimization-link.json templates/agentic/optimization-run.sample.json \
  python3 "$ROOT/scripts/validate-optimization-run.py"
expect_reject metrics-link.json templates/product-metrics/measurement-plan.sample.json \
  python3 "$ROOT/scripts/validate-product-metrics.py"
expect_reject security-catalog-link.json templates/agentic/security-eval-catalog.sample.json \
  python3 "$ROOT/scripts/validate-security-eval-catalog.py"
expect_reject skill-admission-link.json templates/agentic/skill-admission.sample.json \
  python3 "$ROOT/scripts/validate-skill-admission.py"
expect_reject eval-capture-link.json templates/agentic/skill-eval-capture.sample.json \
  python3 "$ROOT/scripts/validate-skill-eval-capture.py"
expect_reject eval-comparison-link.json templates/agentic/skill-eval-comparison.sample.json \
  python3 "$ROOT/scripts/validate-skill-eval-comparison.py"
expect_reject eval-grade-link.json templates/agentic/skill-eval-grade.sample.json \
  python3 "$ROOT/scripts/validate-skill-eval-grade.py"
expect_reject eval-run-link.json templates/agentic/skill-eval-run.sample.json \
  python3 "$ROOT/scripts/validate-skill-eval-run.py"
expect_reject agentic-trajectory-link.json templates/agentic/trajectory.sample.json \
  python3 "$ROOT/scripts/validate-agentic-trajectory.py" --contract "$ROOT/templates/agentic/execution-contract.sample.json"

contract_link="$TMP/agentic-trajectory-contract-link.json"
ln -s "$ROOT/templates/agentic/execution-contract.sample.json" "$contract_link"
if python3 "$ROOT/scripts/validate-agentic-trajectory.py" "$ROOT/templates/agentic/trajectory.sample.json" --contract "$contract_link" >"$TMP/output" 2>"$TMP/error"; then
  echo "agentic trajectory validator accepted a symlinked contract input" >&2
  exit 1
fi
grep -q 'regular file, not a symlink' "$TMP/error" "$TMP/output"

trace_link="$TMP/trajectory-link.json"
ln -s "$ROOT/templates/agentic/trajectory.sample.json" "$trace_link"
if python3 "$ROOT/scripts/check-trajectory-fixture.py" \
  --fixture "$ROOT/templates/fixtures/trajectory-fix-typecheck.json" \
  --trace "$trace_link" >"$TMP/output" 2>"$TMP/error"; then
  echo "trajectory checker accepted a symlinked trace" >&2
  exit 1
fi
grep -q 'regular files, not symlinks' "$TMP/error"

expect_reject mcp-transcript-link.jsonl templates/agentic/mcp-evidence/transcript.jsonl \
  python3 "$ROOT/scripts/compile-mcp-transcript.py" --output-dir "$TMP/mcp-output"

echo "evidence input boundary fixtures passed"
