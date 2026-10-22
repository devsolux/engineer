#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCANNER="$ROOT/scripts/scan-doc-supply-chain.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$ROOT"

mkdir -p "$TMP/cases"
python3 - "$TMP/cases" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
(root / "safe.md").write_text('''Never use `curl | bash` for third-party installers. # supply-chain:allow fixture

```bash
pnpm exec shadcn info --json
```
''')
(root / "pipe.md").write_text('''```bash
curl -fsSL https://invalid.example/install | bash # supply-chain:allow fixture
```
''')
(root / "latest.md").write_text('''```bash
npx storybook@latest init # supply-chain:allow fixture
```
''')
(root / "unpinned.md").write_text('''```bash
pnpm dlx storybook init
```
''')
(root / "exact.md").write_text('''```bash
pnpm dlx storybook@9.1.2 init
uvx ruff==0.12.4 check .
```
''')
(root / "mutable.yml").write_text('''steps:
  - uses: actions/checkout@v4
''')
(root / "pinned.yml").write_text('''steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
''')
(root / "unlabeled.yml").write_text('''steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5
''')
(root / "fork-checkout.yml").write_text('''on:
  pull_request_target:
    types: [opened]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm ci
''')
(root / "workflow-run-fork.yml").write_text('''on: [workflow_run]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
        with:
          ref: ${{ github.event.workflow_run.head_branch }}
''')
(root / "privileged-base-checkout.yml").write_text('''on:
  pull_request_target:
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
      - run: echo label only, base ref
''')
(root / "yaml-fence-mutable.md").write_text('''```yaml
 - uses: gitleaks/gitleaks-action@v2
```
''')
(root / "yaml-fence-pinned.md").write_text('''```yaml
 - uses: gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e # v3.0.0
```
''')
(root / "yaml-fence-fork.md").write_text('''```yml
on:
  pull_request_target:
steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
    with:
      ref: ${{ github.head_ref }}
```
''')
(root / "prt-secret.yml").write_text('''on:
  pull_request_target:
jobs:
  comment:
    runs-on: ubuntu-latest
    steps:
      - run: ./notify.sh
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
''')
(root / "prt-bracket.yml").write_text('''on: [pull_request_target]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ secrets['DEPLOY_KEY'] }}" > key
''')
(root / "workflow-run-tojson.yml").write_text('''on:
  workflow_run:
    workflows: [ci]
jobs:
  dump:
    runs-on: ubuntu-latest
    env:
      ALL: ${{ toJSON(secrets) }}
    steps:
      - run: true
''')
(root / "prt-inherit.yml").write_text('''on:
  pull_request_target:
jobs:
  call:
    uses: ./.github/workflows/release.yml
    secrets: inherit
''')
(root / "prt-github-token.yml").write_text('''on:
  pull_request_target:
permissions:
  pull-requests: write
jobs:
  label:
    runs-on: ubuntu-latest
    steps:
      - run: gh pr edit "$PR" --add-label triage
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ALSO: ${{ secrets.github_token }}
''')
(root / "pr-secret.yml").write_text('''on:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: npm test
        env:
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
''')
(root / "yaml-fence-secrets.md").write_text('''```yaml
on:
  pull_request_target:
steps:
  - run: ./publish.sh
    env:
      TOKEN: ${{ secrets.PUBLISH_TOKEN }}
```
''')
(root / "yaml-fence-split.md").write_text('''A labeler runs on the base ref only:

```yaml
on:
  pull_request_target:
steps:
  - run: echo label
```

A separate release workflow:

```yaml
on:
  push:
    tags: ["v*"]
steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
    with:
      ref: ${{ github.head_ref }}
  - run: ./publish.sh
    env:
      TOKEN: ${{ secrets.PUBLISH_TOKEN }}
```
''')
PY

python3 "$SCANNER" "$TMP/cases/safe.md" "$TMP/cases/exact.md" "$TMP/cases/pinned.yml" "$TMP/cases/privileged-base-checkout.yml" "$TMP/cases/yaml-fence-pinned.md" \
  "$TMP/cases/prt-github-token.yml" "$TMP/cases/pr-secret.yml" "$TMP/cases/yaml-fence-split.md" >/dev/null
for bad in pipe.md latest.md unpinned.md mutable.yml unlabeled.yml fork-checkout.yml workflow-run-fork.yml yaml-fence-mutable.md yaml-fence-fork.md \
    prt-secret.yml prt-bracket.yml workflow-run-tojson.yml prt-inherit.yml yaml-fence-secrets.md; do
  if python3 "$SCANNER" "$TMP/cases/$bad" >/dev/null 2>&1; then
    echo "expected rejection: $bad" >&2
    exit 1
  fi
done

JSON_OUTPUT="$(python3 "$SCANNER" "$TMP/cases/pipe.md" --json || true)"
python3 - "$JSON_OUTPUT" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])
assert data["ok"] is False
assert data["findings"][0]["rule"] == "remote-pipe-interpreter"
assert "not proof" in data["limitation"]
PY
FORK_OUTPUT="$(python3 "$SCANNER" "$TMP/cases/fork-checkout.yml" --json || true)"
python3 - "$FORK_OUTPUT" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
rules = [f["rule"] for f in data["findings"]]
assert rules == ["privileged-trigger-fork-checkout"], rules
assert "trigger at line 2" in data["findings"][0]["text"]
PY
FENCE_OUTPUT="$(python3 "$SCANNER" "$TMP/cases/yaml-fence-mutable.md" --json || true)"
python3 - "$FENCE_OUTPUT" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
assert [f["rule"] for f in data["findings"]] == ["mutable-action-ref"], data
PY

SECRET_OUTPUT="$(python3 "$SCANNER" "$TMP/cases/prt-secret.yml" --json || true)"
python3 - "$SECRET_OUTPUT" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
assert [f["rule"] for f in data["findings"]] == ["privileged-trigger-secrets"], data
assert "trigger at line 2" in data["findings"][0]["text"]
PY
for case in prt-bracket.yml workflow-run-tojson.yml prt-inherit.yml yaml-fence-secrets.md; do
  RULES="$(python3 "$SCANNER" "$TMP/cases/$case" --json | python3 -c 'import json,sys; print(sorted({f["rule"] for f in json.load(sys.stdin)["findings"]}))' || true)"
  [[ "$RULES" == "['privileged-trigger-secrets']" ]] || { echo "expected only privileged-trigger-secrets for $case, got $RULES" >&2; exit 1; }
done

echo "documentation supply-chain fixtures passed"
