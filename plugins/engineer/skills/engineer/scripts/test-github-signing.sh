#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOC="$ROOT/references/git-signing-deploy.md"
GATE="$ROOT/templates/github/verified-deploy-gate.yml"

grep -q 'unknown_key' "$DOC"
grep -q 'Co-authored-by:' "$DOC"
grep -q 'Require signed commits' "$DOC"
grep -q 'github.sha' "$GATE"
grep -q '\.commit\.verification' "$GATE"
grep -q 'test "$verified" = "true"' "$GATE"
! grep -Eq 'pull_request_target|permissions:[[:space:]]*write-all|github\.event\.pull_request\.head\.sha' "$GATE"

echo "github signing fixtures: ok"
