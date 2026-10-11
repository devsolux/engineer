#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

check_action() {
  local action="$1" expected="$2" bad
  if command -v rg >/dev/null 2>&1; then
    bad="$(rg -n "uses: ${action}@" .github/workflows templates/github | grep -Fv "$expected" || true)"
  else
    bad="$(grep -R -n --include='*.yml' --include='*.yaml' "uses: ${action}@" .github/workflows templates/github | grep -Fv "$expected" || true)"
  fi
  if [[ -n "$bad" ]]; then
    echo "stale or mutable ${action} reference:" >&2
    echo "$bad" >&2
    exit 1
  fi
}

check_action actions/checkout 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1'
check_action actions/setup-python 'actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0'
check_action actions/setup-node 'actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1 # v7.1.0'

check_action gitleaks/gitleaks-action 'gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e # v3.0.0'

check_action actions/attest 'actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6 # v4.2.2'
check_action actions/upload-artifact 'actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2'

if grep -R -n --include='*.yml' --include='*.yaml' -E 'node-version:[[:space:]]*20([[:space:]]|$)' .github/workflows templates/github; then
  echo "Node 20 app runtime remains in an executable workflow/template" >&2
  exit 1
fi

grep -Fq 'package-manager-cache: false' .github/workflows/validate.yml
grep -Fq 'runner 2.327.1' research/github-actions-node24-2026-07.md
grep -Fq 'Node 24 LTS' research/github-actions-node24-2026-07.md
echo "GitHub Actions runtime pins: ok"
